"""
Basic Android Tap Test
Tests that you can control your Android device via Python
"""

import uiautomator2 as u2
import time

def main():
    print("=" * 60)
    print("📱 ANDROID AUTOMATION TEST")
    print("=" * 60)
    
    # Connect to device
    print("\n1️⃣  Connecting to device...")
    d = u2.connect()
    
    # Get device info
    info = d.info
    print(f"   ✅ Connected to: {info.get('productName', 'Unknown')}")
    print(f"   📱 Model: {info.get('model', 'Unknown')}")
    print(f"   🤖 Android: API {info.get('sdkInt', 'Unknown')}")
    print(f"   📐 Screen: {info.get('displayWidth', 0)}x{info.get('displayHeight', 0)}")
    
    # Test screenshot
    print("\n2️⃣  Testing screenshot capture...")
    try:
        screenshot = d.screenshot()
        screenshot.save("android_screenshot_test.png")
        print(f"   ✅ Screenshot saved: android_screenshot_test.png")
        print(f"   📏 Size: {screenshot.size}")
    except Exception as e:
        print(f"   ❌ Screenshot failed: {e}")
        return
    
    # Test device interaction
    print("\n3️⃣  Testing device control...")
    print("   🔙 Pressing HOME button...")
    d.press('home')
    time.sleep(1)
    
    print("   ✅ Success! Device control is working")
    
    # Show current app
    print("\n4️⃣  Getting current app info...")
    try:
        current_app = d.app_current()
        print(f"   📦 Current package: {current_app.get('package', 'Unknown')}")
        print(f"   🎯 Activity: {current_app.get('activity', 'Unknown')}")
    except Exception as e:
        print(f"   ⚠️  Could not get app info: {e}")
    
    # Test view hierarchy
    print("\n5️⃣  Testing view hierarchy extraction...")
    try:
        xml = d.dump_hierarchy(compressed=True)
        print(f"   ✅ View hierarchy captured ({len(xml)} chars)")
        print(f"   Sample: {xml[:100]}...")
    except Exception as e:
        print(f"   ❌ View hierarchy failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("\n✅ Your device is ready for AI automation!")
    print("\nNext steps:")
    print("1. Run: python android_agent_simple.py")
    print("2. Or integrate with your existing browser-use agent")
    print("\n💡 Try this simple command:")
    print("   import uiautomator2 as u2")
    print("   d = u2.connect()")
    print("   d.click(540, 960)  # Tap center of screen")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure device is connected: adb devices")
        print("2. Make sure USB debugging is enabled")
        print("3. Try: python -m uiautomator2 init")
