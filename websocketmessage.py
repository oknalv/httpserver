from struct import *


class WebSocketMessage:
    """ Generates a binary web socket message.

    Attributes:
        message (bytearray): the message data.
        type_header (int): a binary int, 0b10 if the message is binary or 0b1 if the message is text.
    """
    __MAX_CHUNK_PAYLOAD_LENGTH = 2 ** 64 - 1

    def __init__(self, message, type_=None):
        self.message = message
        self.type_header = 0b10
        if type_ == "text":
                self.type_header = 0b1

    def get_chunks(self):
        """ Returns a generator of the chunks of the message.

        Yields:
            A bytearray with each message chunk.
        """
        while self.message is not None:
            header = self.type_header
            payload = self.message
            if len(self.message) >= WebSocketMessage.__MAX_CHUNK_PAYLOAD_LENGTH:
                payload = self.message[:WebSocketMessage.__MAX_CHUNK_PAYLOAD_LENGTH]
                self.message = self.message[WebSocketMessage.__MAX_CHUNK_PAYLOAD_LENGTH:]

            else:
                self.message = None
                header += 0b10000000

            chunk = bytearray()
            chunk.append(pack(">B", header))
            payload_length = len(payload)
            if payload_length < 126:
                chunk.append(payload_length)
            elif payload_length < 2**16:
                chunk.append(126)
                chunk.extend(pack(">H", payload_length))
            else:
                chunk.append(127)
                chunk.extend(pack(">Q", payload_length))

            chunk.extend(payload)
            yield chunk
    
    @staticmethod
    def get_close():
        """ Returns a close message.
        
        Returns:
            A bytearray with the close message.
        """
        return bytearray(0b1000100000000000)
