import skytraq_class as sky


gps = sky.Skytraq('COM3', debug=True)


if gps.ser.in_waiting:
    msg_id, msg_payload = gps.read_response()

gps.send_cmd(0x09, b'\x02\x01')
