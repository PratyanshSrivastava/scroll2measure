#!/usr/bin/env python3
"""
Scroll2Measure - Distance Measurer using Mouse Scroll Wheel
Calibrate by rolling 30cm, then measure any distance!
"""

from pynput import mouse
import os
import time

class MouseTape:
    def __init__(self):
        self.scroll_count = 0
        self.calibration_ratio = None
        self.measuring = False
        
    def on_scroll(self, x, y, dx, dy):
        """Callback for scroll wheel events"""
        self.scroll_count += abs(dy)  # Count each scroll tick
    
    def calibrate(self):
        """Calibration: Roll wheel 30cm to establish ratio"""
        print("\n" + "="*50)
        print("Scroll2Measure - CALIBRATION MODE")
        print("="*50)
        print("\n⚠️  IMPORTANT INSTRUCTIONS:")
        print("1. Place your mouse on a flat surface")
        print("2. Use a RULER and mark a 30 CM line")
        print("3. Roll your mouse scroll wheel EXACTLY over 30cm")
        print("4. Start rolling from the first mark")
        print("5. Stop when you reach the 30cm mark")
        print("\n" + "-"*50)
        
        input("Press ENTER when ready to calibrate...")
        
        self.scroll_count = 0
        print("\n⏳ Calibrating... Start rolling NOW!")
        
        # Listen for 10 seconds (enough time to roll 30cm)
        with mouse.Listener(on_scroll=self.on_scroll) as listener:
            time.sleep(10)
        
        if self.scroll_count == 0:
            print("\n❌ ERROR: No scroll detected!")
            print("Make sure you rolled the scroll wheel.")
            return False
        
        # Calculate ratio: scroll_count per 30cm
        self.calibration_ratio = self.scroll_count / 30.0
        
        print(f"\n✅ Calibration complete!")
        print(f"📊 Scroll count: {self.scroll_count}")
        print(f"📐 Ratio: {self.calibration_ratio:.2f} clicks per cm")
        print(f"📏 This means 1 scroll click = {1/self.calibration_ratio:.4f} cm")
        
        return True
    
    def measure(self):
        """Measure mode: Calculate distance from scroll wheel movement"""
        if not self.calibration_ratio:
            print("\n❌ ERROR: Not calibrated! Run calibration first.")
            return

        print("\n" + "="*50)
        print("Scroll2Measure - MEASUREMENT MODE")
        print("="*50)
        print(f"\n📐 Ratio: {self.calibration_ratio:.2f} clicks per cm")
        print("\nPlace your mouse on the starting point of what")
        print("you want to measure, then roll the scroll wheel.")
        print("Press ENTER to stop measuring.\n")

        input("Press ENTER to start measuring...")

        self.scroll_count = 0

        # Start listener in background
        listener = mouse.Listener(on_scroll=self.on_scroll)
        listener.start()

        input("Measuring... Roll the wheel, then press ENTER to stop...")

        # Stop listener after Enter
        listener.stop()
        listener.join()

        if self.scroll_count == 0:
            print("\n⚠️  No scroll detected.")
            return

        # Calculate distance
        distance_cm = self.scroll_count / self.calibration_ratio
        distance_m = distance_cm / 100.0
        distance_mm = distance_cm * 10.0
        distance_inch = distance_cm / 2.54

        print(f"\n✅ Measurement complete!")
        print(f"\n📊 Results:")
        print(f"   Scroll clicks: {self.scroll_count}")
        print(f"   📏 {distance_cm:.2f} cm")
        print(f"   📏 {distance_mm:.1f} mm")
        print(f"   📏 {distance_m:.3f} m")
        print(f"   📏 {distance_inch:.2f} inches")
        print()


    
    def menu(self):
        """Main menu"""
        while True:
            print("\n" + "="*50)
            print("Scroll2Measure - Main Menu")
            print("="*50)
            print("\n1. Calibrate (Required first time)")
            print("2. Measure Distance")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "1":
                if self.calibrate():
                    print("\n💾 Calibration saved!")
            elif choice == "2":
                self.measure()
            elif choice == "3":
                print("\n👋 Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Try again.")

def main():
    mousetape = MouseTape()
    mousetape.menu()

if __name__ == "__main__":
    main()
