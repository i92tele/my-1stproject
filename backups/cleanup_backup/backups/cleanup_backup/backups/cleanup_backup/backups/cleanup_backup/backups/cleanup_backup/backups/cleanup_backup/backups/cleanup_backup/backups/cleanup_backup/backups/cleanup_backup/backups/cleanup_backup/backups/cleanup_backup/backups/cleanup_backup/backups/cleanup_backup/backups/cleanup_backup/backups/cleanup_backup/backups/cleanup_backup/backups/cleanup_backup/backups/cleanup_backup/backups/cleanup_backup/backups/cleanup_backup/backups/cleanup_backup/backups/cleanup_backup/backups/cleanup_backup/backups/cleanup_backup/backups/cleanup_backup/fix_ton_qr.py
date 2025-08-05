#!/usr/bin/env python3
"""
Fix TON QR Code Generation
Creates proper TON payment QR codes that work with exchanges
"""

import qrcode
import os
from dotenv import load_dotenv

def generate_ton_qr_code():
    """Generate a proper TON payment QR code."""
    
    # Load environment
    load_dotenv('config/.env')
    
    # Get TON address from environment
    ton_address = os.getenv('TON_ADDRESS')
    
    if not ton_address:
        print("❌ TON_ADDRESS not found in .env file")
        return
    
    print(f"📱 TON Address: {ton_address}")
    
    # Test amount (1 TON = 1,000,000,000 nanoTON)
    amount_ton = 1.0
    amount_nano = int(amount_ton * 1000000000)
    
    # Create TON payment URI (standard format)
    payment_uri = f"ton://transfer/{ton_address}?amount={amount_nano}"
    
    print(f"🔗 Payment URI: {payment_uri}")
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_uri)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code
    img.save("ton_payment_qr.png")
    print("✅ QR code saved as: ton_payment_qr.png")
    
    # Also create a simple address-only QR code
    qr_simple = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr_simple.add_data(ton_address)
    qr_simple.make(fit=True)
    
    img_simple = qr_simple.make_image(fill_color="black", back_color="white")
    img_simple.save("ton_address_qr.png")
    print("✅ Address-only QR code saved as: ton_address_qr.png")
    
    return payment_uri

def test_with_your_address():
    """Test with your specific address."""
    your_address = "UQAF5N1Eke85knjNZNXz6tIwuiTb_GL6CpIHwT6ifWdcN_Y6"
    
    print(f"\n🧪 Testing with your address: {your_address}")
    
    # Test amount (0.1 TON)
    amount_ton = 0.1
    amount_nano = int(amount_ton * 1000000000)
    
    # Create payment URI
    payment_uri = f"ton://transfer/{your_address}?amount={amount_nano}"
    
    print(f"🔗 Test Payment URI: {payment_uri}")
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("test_payment_qr.png")
    print("✅ Test QR code saved as: test_payment_qr.png")

if __name__ == "__main__":
    print("🔧 Fixing TON QR Code Generation")
    print("=" * 40)
    
    # Generate QR with configured address
    generate_ton_qr_code()
    
    # Test with your specific address
    test_with_your_address()
    
    print("\n💡 Instructions:")
    print("1. Check the generated QR codes")
    print("2. Test with KuCoin withdrawal")
    print("3. Use the address-only QR if payment QR doesn't work")
    print("4. Make sure to send the exact amount shown") 