from skysafe.channels import send_sms

def test_send_sms_channel():
    success = send_sms("+919999999999", "DRILL: Severe weather warning for Cuttack.")
    assert success is True
