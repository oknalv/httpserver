from select import select
from struct import unpack_from

from websocketmessage import WebSocketMessage


class WebSocketHandler:
    """ Handles a basic web socket communication. Its methods `setup` and `received_message` may be extended.
    
    Attributes:
        client (socket.socket): the client socket.
        closed (bool): a flag to close the connection.

    TODO:
        * Change the read method to handle bigger messages and to support more opcodes.
    """
    def __init__(self, client):
        self.client = client
        self.closed = False
        self.setup()

    def setup(self):
        """ Sets up the handler.
        """
        pass

    def received_message(self, message):
        """ Handles the received messages.
        
        Args:
            message (str|bytes): the message to handle.
        """
        pass

    def is_closed(self):
        """ Checks if the connection is closed.
        """ 
        if self.closed:
            return True

        """ This part is for checking if the client closed the connection accidentaly,
        e. g. by closing directly the browser tab. For more info check how select works in Python.
        """
        i, o, e = select([], [self.client], [])
        if o:
            return False

        """ In case the `o` is false, it means it is closed, so we close everything.
        """ 
        self.close()
        return True

    def read(self):
        """ Reads a message from the client. The names of the variables were chosen trying to follow the
        names of the parts of the messages in the WebSocket Protocol specification. The method is easy
        to understand if you understand the protocol and how messages are built. For more information,
        check the specification: https://tools.ietf.org/html/rfc6455
        """
        fin = False
        message = ""
        while not fin:
            first_bytes = bytearray(2)
            self.client.settimeout(0)
            self.client.recv_into(first_bytes)
            fin = first_bytes[0] & 0b10000000 > 0
            rsv = first_bytes[0] & 0b01110000 >> 4
            opcode = first_bytes[0] & 0b00001111
            mask = first_bytes[1] & 0b10000000 > 0
            payload_length = first_bytes[1] & 0b01111111
            payload = None
            masking_key = None
            if payload_length > 0:
                if payload_length == 126:
                    aux_buff = bytearray(2)
                    self.client.recv_into(aux_buff)
                    payload_length = unpack_from(">H", aux_buff)

                elif payload_length == 127:
                    aux_buff = bytearray(8)
                    self.client.recv_into(aux_buff)
                    payload_length = unpack_from(">Q", aux_buff)

            if mask:
                masking_key = bytearray(4)
                self.client.recv_into(masking_key)

            if payload_length > 0:
                payload = bytearray(payload_length)
                self.client.recv_into(payload, payload_length)

            if opcode == 8:
                self.closed = True
                self.client.close()
                return

            elif not (opcode == 1 or opcode == 0):
                raise OpcodeNotSupportedException(opcode)

            else:
                if not mask and payload_length > 0:
                    raise NotMaskedException()

                elif payload is not None:
                    for i in range(payload_length):
                        payload[i] ^= masking_key[i % 4]

                    message += str(payload)

        self.received_message(message)

    def close(self):
        """ Closes the connection.
        """
        self.closed = True
        try:
            self.client.settimeout(None)
            self.client.send(WebSocketMessage.get_close())
            self.client.close()
        except:
            pass


class OpcodeNotSupportedException(Exception):
    """ An exception to be thrown when an opcode is not supported, when all opcodes are supported,
    it should be deleted.
    """
    def __init__(self, opcode):
        self.message = "opcode " + str(opcode) + " not supported."


class NotMaskedException(Exception):
    """ An expception to be thrown when the message is not masked.
    """
    pass
