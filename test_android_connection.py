"""
Android Connection Test
Quick verification that your device is connected and ready for automation
"""

import subprocess
import sys

def check_adb():
    """Check if ADB is accessible"""
    try:
        result = subprocess.run(['adb', '--version'], capture_output=True, text=True)
        print("✅ ADB is installed")
        print(f"   Version: {result.stdout.split()[4]}")
        return True
    except FileNotFoundError:
        print("❌ ADB not found. Please install Android SDK Platform Tools")
        return False

def list_devices():
    """List connected Android devices"""
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')[1:]  # Skip header
    
    devices = [line.split()[0] for line in lines if line.strip() and 'device' in line]
    
    if not devices:
        print("\n❌ No devices found!")
        print("\n📱 Next steps:")
        print("1. Connect your Android device via USB")
        print("2. Enable 'USB Debugging' in Developer Options:")
        print("   Settings → About Phone → Tap 'Build Number' 7 times")
        print("   Settings → Developer Options → Enable 'USB Debugging'")
        print("3. Run this script again")
        return None
    
    print(f"\n✅ Found {len(devices)} device(s):")
    for i, device in enumerate(devices, 1):
        print(f"   {i}. {device}")
    
    return devices[0]  # Return first device

def test_device_connection(device_id):
    """Test basic device communication"""
    try:
        # Get device info
        result = subprocess.run(
            ['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model'],
            capture_output=True,
            text=True,
            timeout=5
        )
        model = result.stdout.strip()
        
        result = subprocess.run(
            ['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'],
            capture_output=True,
            text=True,
            timeout=5
        )
        android_version = result.stdout.strip()
        
        print(f"\n✅ Device connected successfully!")
        print(f"   Model: {model}")
        print(f"   Android Version: {android_version}")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"\n❌ Device not responding. Try:")
        print("   1. Unplug and replug USB cable")
        print("   2. Accept 'Allow USB debugging' dialog on phone")
        return False
    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        return False

def check_uiautomator2():
    """Check if uiautomator2 is installed"""
    try:
        import uiautomator2
        print("\n✅ uiautomator2 Python package is installed")
        try:
            import pkg_resources
            version = pkg_resources.get_distribution("uiautomator2").version
            print(f"   Version: {version}")
        except:
            print("   Version: Unknown")
        return True
    except ImportError:
        print("\n⚠️  uiautomator2 not installed")
        print("   Installing now...")
        return False

def main():
    print("=" * 60)
    print("🔧 ANDROID AUTOMATION SETUP TEST")
    print("=" * 60)
    
    # Step 1: Check ADB
    if not check_adb():
        sys.exit(1)
    
    # Step 2: List devices
    device = list_devices()
    if not device:
        sys.exit(1)
    
    # Step 3: Test connection
    if not test_device_connection(device):
        sys.exit(1)
    
    # Step 4: Check uiautomator2
    if not check_uiautomator2():
        print("\n⏳ Installing uiautomator2...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'uiautomator2'])
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext step: Run the following command to initialize uiautomator2:")
    print(f"   python -m uiautomator2 init")
    print("\nThen test basic automation:")
    print(f"   python test_android_tap.py")

if __name__ == "__main__":
    main()
