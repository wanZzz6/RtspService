from rtsp.auth import digest
import unittest

## Example Traffic
"""
DESCRIBE rtsp://192.168.201.14:554/h264/ch1/sub/av_stream RTSP/1.0 
Accept: application/sdp 
CSeq: 2 
User-Agent: Lavf58.20.100 

RTSP/1.0 401 Unauthorized 
CSeq: 2 
WWW-Authenticate: Digest realm="IP Camera(D4918)", nonce="325dbaf043b7cba36b17da397381f421", stale="FALSE" 
Date:  Tue, Jan 28 2020 23:50:09 GMT 

DESCRIBE rtsp://192.168.201.14:554/h264/ch1/sub/av_stream RTSP/1.0 
Accept: application/sdp 
CSeq: 3 
User-Agent: Lavf58.20.100 
Authorization: Digest username="admin", realm="IP Camera(D4918)", nonce="325dbaf043b7cba36b17da397381f421", uri="rtsp://192.168.201.14:554/h264/ch1/sub/av_stream", response="7b616f558394d1f3f65fc852c353dcc1" 
"""


class test_asmrp(unittest.TestCase):
    def test_rn5(self):
        """
        token from a wireshark capture with RealPlayer with the auth data
        admin:tsit2019
        """
        result = digest(username='admin', password='tsit2019',
                        realm='IP Camera(D4918)',
                        method="DESCRIBE",
                        uri="rtsp://192.168.201.14:554/h264/ch1/sub/av_stream",
                        nonce='325dbaf043b7cba36b17da397381f421',
                        )
        self.assertEqual('7b616f558394d1f3f65fc852c353dcc1', result)


if __name__ == '__main__':
    unittest.main()
