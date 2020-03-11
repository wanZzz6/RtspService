from rtsp.sdpp import SdpParser

a = """
v=0 
o=- 1580255409340549 1580255409340549 IN IP4 192.168.201.14 
s=Media Presentation 
e=NONE 
b=AS:5050 
t=0 0 
a=control:rtsp://192.168.201.14:554/h264/ch1/sub/av_stream/ 
m=video 0 RTP/AVP 96 
c=IN IP4 0.0.0.0 
b=AS:5000 
a=recvonly 
a=x-dimensions:704,576 
a=control:rtsp://192.168.201.14:554/h264/ch1/sub/av_stream/trackID=1 
a=rtpmap:96 H264/90000 
a=fmtp:96 profile-level-id=420029; packetization-mode=1; sprop-parameter-sets=Z00AHpY1QWAk03AQEBQAABwgAAV+QBA=,aO48gA== 
a=Media_header:MEDIAINFO=494D4B48010200000400000100000000000000000000000000000000000000000000000000000000; 
a=appversion:1.0 
"""

p = SdpParser()
session, media = p.parse(a)
print(p.session)
print(p.session.session_desc)
print(p.media[0])

print(session.to_str())
print(media[0].to_str())
p.save_as_json('aa.json')

p.loadJson('aa.json')

print(p.build_self())
