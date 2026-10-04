from paybridge.domain.pii_policy import mask_account_number, mask_ifsc, mask_name

def test_NFR_03_account_masked(): assert mask_account_number('123456789012') == '********9012'
def test_NFR_03_ifsc_masked(): assert mask_ifsc('ABCD0123456') == 'ABCD*****56'
def test_NFR_03_name_masked(): assert mask_name('Demo User') == 'D*** U***'
