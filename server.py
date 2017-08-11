from ironman.constructs.ipbus import PacketHeaderStruct, ControlHeaderStruct, IPBusConstruct, IPBusWords
from ironman.hardware import HardwareManager, HardwareMap
from ironman.communicator import Jarvis
import random

j = Jarvis()
manager = HardwareManager()

manager.add(HardwareMap(file('hardware_map.yml').read(), 'main'))
j.set_hardware_manager(manager)

@j.register('main')
class RandomNumberGeneratorController:
  __low__  = 0
  __high__ = 9
  def read(self, offset, size):
    if offset == 0x0:
      number = random.randint(self.__class__.__low__, self.__class__.__high__)
      return str(number)[:size*4].rjust(4, "\0")
    elif offset == 0x1:
      return str(self.__class__.__low__)[:size*4].rjust(4, "\0")
    elif offset == 0x2:
      return str(self.__class__.__high__)[:size*4].rjust(4, "\0")

  def write(self, offset, data):
    if offset == 0x0:
      return
    elif offset == 0x1:
      self.__class__.__low__ = int(data[0])
      return
    elif offset == 0x2:
      self.__class__.__high__ = int(data[0])
      return

def buildResponsePacket(packet):
    packet.response.data[0].info_code = 'SUCCESS'
    #packet.response.data[0].data = [packet.response.data[0].data]
    return IPBusConstruct.build(packet.response)
    # data += PacketHeaderStruct.build(packet.response.header)
    # for transaction, response in zip(packet.response.data, packet.response):
    #     data += ControlHeaderStruct.build(transaction)
    #     data += response.encode("hex").decode("hex")
    return data


from ironman.history import History
h = History()

from ironman.server import ServerFactory
from ironman.packet import IPBusPacket
from twisted.internet import reactor
from twisted.internet.defer import Deferred

def deferredGenerator():
    return Deferred().addCallback(IPBusPacket).addCallback(j).addCallback(buildResponsePacket)#.addCallback(h.record)

reactor.listenUDP(8888, ServerFactory('udp', deferredGenerator))

'''set up a mirror web server for IPBus requests'''
# Site, an IProtocolFactory which glues a listening server port (IListeningPort) to the HTTPChannel implementation
from twisted.web.server import Site
from twisted.web.resource import Resource
# deferred responses
from twisted.web.server import NOT_DONE_YET
# return json
import json
class HTTPIPBusRoot(Resource):
    # has children
    isLeaf = False

class HTTPIPBus(Resource):
    # no children
    isLeaf = True
    def render_GET(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        # request.postpath will contain what we need
        if len(request.postpath) != 3 and len(request.postpath) != 4:
            return json.dumps({
                "success": False,
                "data": None,
                "error": "Incorrect number of URL segments",
                "traceback": None
            })

        # make sure we can convert to hex string
        for i, word in enumerate(request.postpath):
            if len(word) != 8:
                return json.dumps({
                    "success": False,
                    "data": None,
                    "error": "Word {:d} has incorrect length {:d}. It should be: 8.".format(i, len(word)),
                    "traceback": None})

        packet = ''.join(request.postpath)
        try:
            packet.decode("hex")
        except TypeError as e:
            import sys
            return json.dumps({
                "success": False,
                "data": None,
                "error": str(e),
                "traceback": str(sys.exc_info())
            })

        def write(result):
            packet = IPBusConstruct.parse(result)
            data = None
            if packet.data[0].type_id == 'READ':
              data = IPBusWords.build(packet.data[0])
            request.write(json.dumps({
                "success": True,
                "data": data,
                "error": None,
                "traceback": None
            }))
            request.finish()

        def error(result):
            request.write(json.dumps({
                "success": False,
                "data": None,
                "error": "An unknown error has occurred with the application. Message: {0}".format(result.getErrorMessage()),
                "traceback": result.getBriefTraceback()
            }))
            request.finish()

        d = deferredGenerator()
        d.addCallbacks(write, error)
        print("Handling IPBus packet {0:s}".format(packet))
        d.callback(packet.decode('hex'))
        return NOT_DONE_YET

http_ipbus_root = HTTPIPBusRoot()
http_ipbus_root.putChild('ipbus', HTTPIPBus())
reactor.listenTCP(7777, Site(http_ipbus_root))

reactor.run()
