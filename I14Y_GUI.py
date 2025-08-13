import tkinter as tk
import subprocess
import os
import sys

def check_versions():
    print(f"Python version: {sys.version}")
    print(f"Tkinter version: {tk.TclVersion}")
    version_label.config(text=f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} | Tkinter: {tk.TclVersion}")

def run_transform():
    print("Button clicked! Running transform...")
    
    # The exact command you want to run
    cmd = [
        "python", "AD_I14Y_transformator.py", 
        "PGR", "SNE", 
        "./AD_VS/XML", "./AD_VS/Transformed", 
        "2025-08-12"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ SUCCESS!")
            # Update text widget instead of label
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "✅ Transform completed successfully!\n\n")
            output_text.insert(tk.END, result.stdout)
        else:
            print("❌ FAILED!")
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "❌ Transform failed!\n\n")
            output_text.insert(tk.END, f"Error: {result.stderr}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"❌ Error: {e}")

# Create the window
root = tk.Tk()
root.title("Simple Transform - Mac Label Bug Workaround")
root.geometry("600x400")

# Version info at top
version_label = tk.Label(root, text="Checking versions...", font=("Arial", 10), bg="lightgray")
version_label.pack(pady=5, fill=tk.X)

# Warning about Mac bug
warning_text = tk.Text(root, height=3, font=("Arial", 10), bg="lightyellow")
warning_text.insert(tk.END, "MAC BUG: If you're using Python 3.9.6, labels won't show!\n")
warning_text.insert(tk.END, "Solution: Install Python 3.12+ from python.org\n")
warning_text.insert(tk.END, "Using Text widgets instead of Labels as workaround...")
warning_text.pack(pady=5, fill=tk.X)

# Big transform button
transform_button = tk.Button(
    root, 
    text="RUN TRANSFORM", 
    command=run_transform,
    font=("Arial", 14),
    bg="red",
    fg="white",
    width=20,
    height=2
)
transform_button.pack(pady=10)

# Output using Text widget (this should work even with the bug)
output_text = tk.Text(root, font=("Courier", 10), bg="white", fg="black")
output_text.insert(tk.END, "Ready - Click button to start transform\n")
output_text.insert(tk.END, "(Output will appear here)\n")
output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Check versions on startup
check_versions()

print("GUI created with Mac bug workaround...")
root.mainloop()