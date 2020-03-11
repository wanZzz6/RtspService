import io
from http.client import HTTPMessage
from urllib.parse import urlparse
import http

import email

# maximal amount of data to read at one time in _safe_read
MAXAMOUNT = 1048576
_UNKNOWN = 'UNKNOWN'
_MAXLINE = 65536
_MAXHEADERS = 100

# globals().update(http.HTTPStatus.__members__)
CONTINUE = http.HTTPStatus.CONTINUE
NO_CONTENT = http.HTTPStatus.NO_CONTENT
NOT_MODIFIED = http.HTTPStatus.NOT_MODIFIED


def parse_headers(fp, _class=HTTPMessage):
    """Parses only RFC2822 headers from a file pointer.

    email Parser wants to see strings rather than bytes.
    But a TextIOWrapper around self.rfile would buffer too many bytes
    from the stream, bytes which we later need to read as bytes.
    So we read the correct bytes here, as bytes, for email Parser
    to parse.

    """
    headers = []
    while True:
        line = fp.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise LineTooLong("header line")
        headers.append(line)
        if len(headers) > _MAXHEADERS:
            raise RTSPException("got more than %d headers" % _MAXHEADERS)
        if line in ('\r\n', '\n', ''):
            break
    hstring = ''.join(headers)
    return email.parser.Parser(_class=_class).parsestr(hstring)


class RTSPResponse(io.BufferedIOBase):

    # See RFC 2616 sec 19.6 and RFC 1945 sec 6 for details.

    # The bytes from the socket object are iso-8859-1 strings.
    # See RFC 2616 sec 2.2 which notes an exception for MIME-encoded
    # text following RFC 2047.  The basic status line parsing only
    # accepts iso-8859-1.

    def __init__(self, string_io, debuglevel=0, method=None):
        # If the response includes a content-length header, we need to
        # make sure that the client doesn't read more than the
        # specified number of bytes.  If it does, it will block until
        # the server times out and closes the connection.  This will
        # happen if a self.fp.read() is done (without a size) whether
        # self.fp is buffered or not.  So, no self.fp.read() by
        # clients unless they know what they are doing.
        self.fp = string_io
        self.debuglevel = debuglevel
        self._method = method

        self.headers = self.msg = None

        # from the Status-Line of the response
        self.version = _UNKNOWN  # RTSP-Version
        self.status = _UNKNOWN  # Status-Code
        self.reason = _UNKNOWN  # Reason-Phrase

        self.length = _UNKNOWN  # number of bytes left in response
        self.body = self.content = _UNKNOWN

        self.begin()

    def __repr__(self):
        return '<Response [%s]>' % self.status

    def _read_first_line(self):
        line = self.fp.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise LineTooLong("status line")
        if self.debuglevel > 0:
            print("reply:", repr(line))
        if not line:
            # Presumably, the server closed the connection before
            # sending a valid response.
            raise RemoteDisconnected("Remote end closed connection without"
                                     " response")
        try:
            version, status, reason = line.split(None, 2)
        except ValueError:
            try:
                version, status = line.split(None, 1)
                reason = ""
            except ValueError:
                # empty version will cause next test to fail.
                version = ""
        if not version.startswith("RTSP/"):
            self._close_conn()
            raise BadStatusLine(line)

        # The status code is a three-digit number
        try:
            status = int(status)
            if status < 100 or status > 999:
                raise BadStatusLine(line)
        except ValueError:
            raise BadStatusLine(line)
        return version, status, reason

    def begin(self):
        # todo xxx
        if self.headers is not None:
            # we've already started reading the response
            return

        # read until we get a non-100 response
        while True:
            version, status, reason = self._read_first_line()
            if status != CONTINUE:
                break
                # todo xxx
            # skip the header from the 100 response
            while True:
                skip = self.fp.readline(_MAXLINE + 1)
                if len(skip) > _MAXLINE:
                    raise LineTooLong("header line")
                skip = skip.strip()
                if not skip:
                    break
                if self.debuglevel > 0:
                    print("header:", skip)

        self.code = self.status = status
        self.reason = reason.strip()
        if version.startswith("RTSP/2."):
            self.version = 2
        elif version.startswith("RTSP/1."):
            self.version = 1
        else:
            raise UnknownProtocol(version)

        self.headers = self.msg = parse_headers(self.fp)

        if self.debuglevel > 0:
            for hdr in self.headers:
                print("header:", hdr + ":", self.headers.get(hdr))

        # do we have a Content-Length?
        self.length = None
        length = self.headers.get("content-length")

        if length:
            try:
                self.length = int(length)
            except ValueError:
                self.length = None
            else:
                if self.length < 0:  # ignore nonsensical negative lengths
                    self.length = None
        else:
            self.length = None
        # todo body length
        self.body = self.content = self.read()

    def _close_conn(self):
        fp = self.fp
        self.fp = None
        fp.close()

    def close(self):
        try:
            super().close()  # set "closed" flag
        finally:
            if self.fp:
                self._close_conn()

    # These implementations are for the benefit of io.BufferedReader.

    # XXX This class should probably be revised to act more like
    # the "raw stream" that BufferedReader expects.

    def flush(self):
        super().flush()
        if self.fp:
            self.fp.flush()

    def readable(self):
        """Always returns True"""
        return True

    # End of "raw stream" methods

    def isclosed(self):
        """True if the connection is closed."""
        # NOTE: it is possible that we will not ever call self.close(). This
        #       case occurs when will_close is TRUE, length is None, and we
        #       read up to the last byte, but NOT past it.
        #
        # IMPLIES: if will_close is FALSE, then self.close() will ALWAYS be
        #          called, meaning self.isclosed() is meaningful.
        return self.fp is None

    def read(self, amt=None):
        if self.fp is None:
            return b""

        if self._method == "HEAD":
            self._close_conn()
            return b""

        if amt is not None:
            # Amount is given, implement using readinto
            b = bytearray(amt)
            n = self.readinto(b)
            return memoryview(b)[:n].tobytes()
        else:
            if self.length is None:
                s = self.fp.read()
            else:
                try:
                    s = self._safe_read(self.length)
                except IncompleteRead:
                    self._close_conn()
                    raise
                self.length = 0
            self._close_conn()  # we read everything
            return s

    def readinto(self, b):
        """Read up to len(b) bytes into bytearray b and return the number
        of bytes read.
        """

        if self.fp is None:
            return 0

        if self._method == "HEAD":
            self._close_conn()
            return 0

        if self.length is not None:
            if len(b) > self.length:
                # clip the read to the "end of response"
                b = memoryview(b)[0:self.length]

        # we do not use _safe_read() here because this may be a .will_close
        # connection, and the user is reading more bytes than will be provided
        # (for example, reading in 1k chunks)
        n = self.fp.readinto(b)
        if not n and b:
            # Ideally, we would raise IncompleteRead if the content-length
            # wasn't satisfied, but it might break compatibility.
            self._close_conn()
        elif self.length is not None:
            self.length -= n
            if not self.length:
                self._close_conn()
        return n

    def _read_and_discard_trailer(self):
        # read and discard trailer up to the CRLF terminator
        ### note: we shouldn't have any trailers!
        while True:
            line = self.fp.readline(_MAXLINE + 1)
            if len(line) > _MAXLINE:
                raise LineTooLong("trailer line")
            if not line:
                # a vanishingly small number of sites EOF without
                # sending the trailer
                break
            if line in (b'\r\n', b'\n', b''):
                break

    def _safe_read(self, amt):
        """Read the number of bytes requested, compensating for partial reads.

        Normally, we have a blocking socket, but a read() can be interrupted
        by a signal (resulting in a partial read).

        Note that we cannot distinguish between EOF and an interrupt when zero
        bytes have been read. IncompleteRead() will be raised in this
        situation.

        This function should be used when <amt> bytes "should" be present for
        reading. If the bytes are truly not available (due to EOF), then the
        IncompleteRead exception can be used to detect the problem.
        """
        s = []
        while amt > 0:
            chunk = self.fp.read(min(amt, MAXAMOUNT))
            s.append(chunk)
            amt -= len(chunk)
        return "".join(s)

    def _safe_readinto(self, b):
        """Same as _safe_read, but for reading into a buffer."""
        total_bytes = 0
        mvb = memoryview(b)
        while total_bytes < len(b):
            if MAXAMOUNT < len(mvb):
                temp_mvb = mvb[0:MAXAMOUNT]
                n = self.fp.readinto(temp_mvb)
            else:
                n = self.fp.readinto(mvb)
            if not n:
                raise IncompleteRead(bytes(mvb[0:total_bytes]), len(b))
            mvb = mvb[n:]
            total_bytes += n
        return total_bytes

    def read1(self, n=-1):
        """Read with at most one underlying system call.  If at least one
        byte is buffered, return that instead.
        """
        if self.fp is None or self._method == "HEAD":
            return b""
        if self.length is not None and (n < 0 or n > self.length):
            n = self.length
        result = self.fp.read1(n)
        if not result and n:
            self._close_conn()
        elif self.length is not None:
            self.length -= len(result)
        return result

    def peek(self, n=-1):
        # Having this enables IOBase.readline() to read more than one
        # byte at a time
        if self.fp is None or self._method == "HEAD":
            return b""
        return self.fp.peek(n)

    def readline(self, limit=-1):
        if self.fp is None or self._method == "HEAD":
            return b""
        if self.length is not None and (limit < 0 or limit > self.length):
            limit = self.length
        result = self.fp.readline(limit)
        if not result and limit:
            self._close_conn()
        elif self.length is not None:
            self.length -= len(result)
        return result

    def fileno(self):
        return self.fp.fileno()

    def getheader(self, name, default=None):
        """Returns the value of the header matching *name*.

        If there are multiple matching headers, the values are
        combined into a single string separated by commas and spaces.

        If no matching header is found, returns *default* or None if
        the *default* is not specified.

        If the headers are unknown, raises http.client.ResponseNotReady.

        """
        if self.headers is None:
            raise ResponseNotReady()
        headers = self.headers.get_all(name) or default
        if isinstance(headers, str) or not hasattr(headers, '__iter__'):
            return headers
        else:
            return ', '.join(headers)

    def getheaders(self):
        """Return list of (header, value) tuples."""
        if self.headers is None:
            raise ResponseNotReady()
        return list(self.headers.items())

    # We override IOBase.__iter__ so that it doesn't check for closed-ness

    def __iter__(self):
        return self

    # For compatibility with old-style urllib responses.

    def info(self):
        """Returns an instance of the class mimetools.Message containing
        meta-information associated with the URL.

        When the method is HTTP, these headers are those returned by
        the server at the head of the retrieved HTML page (including
        Content-Length and Content-Type).

        When the method is FTP, a Content-Length header will be
        present if (as is now usual) the server passed back a file
        length in response to the FTP retrieval request. A
        Content-Type header will be present if the MIME type can be
        guessed.

        When the method is local-file, returned headers will include
        a Date representing the file's last-modified time, a
        Content-Length giving file size, and a Content-Type
        containing a guess at the file's type. See also the
        description of the mimetools module.

        """
        return self.headers

    def geturl(self):
        """Return the real URL of the page.

        In some cases, the HTTP server redirects a client to another
        URL. The urlopen() function handles this transparently, but in
        some cases the caller needs to know which URL the client was
        redirected to. The geturl() method can be used to get at this
        redirected URL.

        """
        return self.url

    def getcode(self):
        """Return the HTTP status code that was sent with the response,
        or None if the URL is not an HTTP URL.

        """
        return self.status


# todo fake sock makefile
class RTSPRequest(object):
    def __init__(self, string_io, debuglevel=0):
        self.fp = string_io
        self.debuglevel = debuglevel

        self.headers = self.msg = None
        self.body = self.content = None
        self.method = _UNKNOWN
        self.version = _UNKNOWN  # RTSP-Version
        self.url = _UNKNOWN
        self.path = _UNKNOWN
        self.begin()

    def __repr__(self):
        return '<Resuest [%s]>' % self.url

    def _read_first_line(self):
        line = self.fp.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise LineTooLong("status line")
        if self.debuglevel > 0:
            print("reply:", repr(line))
        if not line:
            # Presumably, the server closed the connection before
            # sending a valid response.
            raise RemoteDisconnected("Remote end closed connection without"
                                     " response")
        try:
            method, url, version = line.split(None, 2)
        except ValueError:
            try:
                method, url = line.split(None, 1)
                version = ""
            except:
                # empty version will cause next test to fail.
                raise RTSPException('Invalid Request %s' % line)
        if not version.startswith("RTSP/"):
            self._close_conn()
            raise BadStatusLine(line)

        return method, version, url

    def begin(self):
        if self.headers is not None:
            return self

        method, version, url = self._read_first_line()
        self.method = method
        self.url = url

        u = urlparse(url)
        self.path = u.path
        # todo xxx
        # self.params = u.params
        # self.query = u.query

        if version.startswith("RTSP/2."):
            self.version = 2
        elif version.startswith("RTSP/1."):
            self.version = 1
        else:
            raise UnknownProtocol(version)

        self.headers = self.msg = parse_headers(self.fp)
        if self.debuglevel > 0:
            for hdr in self.headers:
                print("header:", hdr + ":", self.headers.get(hdr))
        self.body = self.content = self.read()

    def read(self):
        if self.fp is None:
            return b""
        s = self.fp.read()
        self._close_conn()  # we read everything
        return s

    def _close_conn(self):
        fp = self.fp
        self.fp = None
        fp.close()


class RTSPException(Exception):
    # Subclasses that define an __init__ must call Exception.__init__
    # or define self.args.  Otherwise, str() will fail.
    pass


class ImproperConnectionState(RTSPException):
    pass


class CannotSendRequest(ImproperConnectionState):
    pass


class CannotSendHeader(ImproperConnectionState):
    pass


class ResponseNotReady(ImproperConnectionState):
    pass


class IncompleteRead(RTSPException):
    def __init__(self, partial, expected=None):
        self.args = partial,
        self.partial = partial
        self.expected = expected

    def __repr__(self):
        if self.expected is not None:
            e = ', %i more expected' % self.expected
        else:
            e = ''
        return '%s(%i bytes read%s)' % (self.__class__.__name__,
                                        len(self.partial), e)

    def __str__(self):
        return repr(self)


class BadStatusLine(RTSPException):
    def __init__(self, line):
        if not line:
            line = repr(line)
        self.args = line,
        self.line = line


class UnknownProtocol(RTSPException):
    def __init__(self, version):
        self.args = version,
        self.version = version


class LineTooLong(RTSPException):
    def __init__(self, line_type):
        RTSPException.__init__(self, "got more than %d bytes when reading %s"
                               % (_MAXLINE, line_type))


class RemoteDisconnected(ConnectionResetError, BadStatusLine):
    def __init__(self, *pos, **kw):
        BadStatusLine.__init__(self, "")
        ConnectionResetError.__init__(self, *pos, **kw)
