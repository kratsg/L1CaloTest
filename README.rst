Installing
==========

To install::

  pip install -r requirements.txt

Running
=======

Run the server first::

  python server.py

This server makes your computer an IPBus target that can respond to IPBus requests. This is set up over UDP at port 8888. There is also an HTTP server running at port 7777 that maps HTTP requests to actionable IPBus requests for you. We'll discuss the latter example as most people have a browser, but not an easy way to send a UDP packet.

Open your browser and point it at:

- http://localhost:7777/ipbus/200000f0/2000010f/00000000 (``0x0``)
- http://localhost:7777/ipbus/200000f0/2000010f/00000001 (``0x1``)
- http://localhost:7777/ipbus/200000f0/2000010f/00000002 (``0x2``)

These are three different read requests at different addresses. ``0x0`` generates a random number, ``0x1`` returns the minimum integer for the generator, and ``0x2`` returns the maximum integer for the generator. To see that this is the case, you can open up a new terminal, run python, and type the following::

  from ironman.constructs.ipbus import IPBusConstruct
  url = 'http://localhost:7777/ipbus/200000f0/2000010f/00000000'
  raw = url.split('ipbus')[-1].replace('/','')
  p = IPBusConstruct.parse(raw.decode('hex'))
  Container:
      header = Container:
	  protocol_version = 2
	  reserved = 0
	  id = 0
	  byteorder = 15
	  type_id = 'CONTROL'
      data = [
	  Container:
	      protocol_version = 2
	      id = 0
	      words = 1
	      type_id = 'READ'
	      info_code = 'REQUEST'
	      address = 0
	      data = None
      ]

which dumps an understandable representation of the request itself. Now, let's make a write request to set the upper limit of the random number generator to 15. Continuing with the above example...::

  from ironman.constructs.ipbus import IPBusConstruct
  raw = '200000f02000010f00000000'
  p = IPBusConstruct.parse(raw.decode('hex'))
  p.data[0].type_id = 'WRITE'
  p.data[0].address = 0x2
  p.data[0].data = [15]
  new_raw = IPBusConstruct.build(p).encode('hex')
  new_url = 'http://localhost:7777/ipbus/{0:s}'.format('/'.join([new_raw[i:i+8] for i in range(0, len(new_raw), 8)]))
  print new_url

which gives me the following URL

- http://localhost:7777/ipbus/200000f0/2000011f/00000002/0000000f

which I can visit in my browser, write the new value, and then visit

- http://localhost:7777/ipbus/200000f0/2000010f/00000002

to read the value again, verify that it has been set, and then refresh

- http://localhost:7777/ipbus/200000f0/2000010f/00000000

over and over again to see the changes take effect immediately.
