import struct
import serial


class Skytraq:
    MSG_TYPE_ACK = 0x83
    MSG_TYPE_NACK = 0x84

    def __init__(self, com, baudrate=9600, debug=False):
        self.debug = debug
        self.ser = serial.Serial(com, baudrate, timeout=5)

    def __del__(self):
        if hasattr(self, 'ser'):
            self.ser.close()

    def read_response(self, max_attempts=256):
        attempt = 0
        prev = 0
        tmp = bytearray()

        # look for start of sequence
        while attempt < max_attempts:
            c = self.ser.read()
            if c[0] == 0xA1 and prev == 0xA0:
                break
            tmp += c
            prev = c[0]
            attempt += 1
        if attempt >= max_attempts:
            raise Exception("failed to get response after reading %d bytes" % attempt, tmp)

        # read length
        payload_len = int(struct.unpack('>H', self.ser.read(2))[0])
        msg_id = self.ser.read()[0]
        payload = self.ser.read(payload_len - 1)

        # validate checksum
        cs = self.ser.read()[0]
        check = 0 ^ msg_id
        for b in payload:
            check ^= b
        if check != cs:
            raise Exception("received msg with invalid checksum", check, cs)

        # read end of sequence
        eos = self.ser.read(2)
        if eos != b"\r\n":
            raise Exception("invalid end of sequence", eos)

        # return msg id and payload
        if self.debug:
            print("RX <-", payload_len, msg_id, payload.hex())
        return msg_id, payload

    def send_cmd(self, msg_id, msg_payload=None, max_attempts=5):
        # start of sequence
        msg = bytearray([0xA0, 0xA1])

        # payload length
        if msg_payload is None:
            payload_len = 1
        else:
            payload_len = 1 + len(msg_payload)

        # append payload
        msg += struct.pack('>H', payload_len)
        msg.append(msg_id)
        if msg_payload is not None:
            msg += msg_payload

        # checksum
        cs = 0
        cs ^= msg_id
        if msg_payload is not None:
            for b in msg_payload:
                cs ^= b
        msg.append(cs)

        # end of sequence
        msg += b'\x0D\x0A'

        # send command
        if self.debug:
            print("TX ->", msg.hex())
        self.ser.write(msg)

        # check acknowledge
        i = 0
        while i < max_attempts:
            rep_id, rep_payload = self.read_response()
            if rep_id == self.MSG_TYPE_NACK:
                if rep_payload[0] == msg_id:
                    raise Exception("gps sent NACK")
            elif rep_id == self.MSG_TYPE_ACK:
                if rep_payload[0] == msg_id:
                    if self.debug:
                        print("gps sent ACK")
                    break
            elif self.debug:
                print("received unexpected", rep_id, rep_payload.hex())
            i += 1

        if i >= max_attempts:
            raise Exception("failed to get ACK for query")
