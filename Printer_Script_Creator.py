import subprocess
import re
import csv
import datetime
import argparse

# This script generates a .csv and .sh. If you run the SH script it will install the printers. You can also edit the CSV and remove Yes to have the script query the printer for the correct driver to have the image appear better.
# Use Platypus to turn this into an app



def run_command(command):
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        print("Error:", result.stderr.strip())
        return None

def get_printer_ip(printer_name):
    ping_output = run_command(f"ping {printer_name} -c 1")
    if ping_output:
        ip_match = re.search(r'\(([0-9.]+)\)', ping_output)
        if ip_match:
            return ip_match.group(1)
    return None

def generate_installer_script(csv_file, script_file):
    with open(script_file, 'w') as script:
        # Self Service Printers
        script.write("#!/bin/bash\n")
        script.write("sudo /usr/sbin/dseditgroup -o edit -a everyone -t group lpadmin\n\n")

        with open(csv_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            increment = 1
            for row in reader:
                desired_name = row[0].strip()
                hostname = row[1].strip()
                ip = row[2].strip()
                driver = row[3].strip()

                ppd_file = f"/private/tmp/printer_driver_{increment:02d}.ppd"

                if not desired_name:
                    desired_name = hostname.split('.')[0]

                if driver.lower() == 'yes':
                    command = f"lpadmin -p \"{desired_name}\" -D \"{desired_name}\" -o printer-is-shared=false -v lpd://{ip}:631/ipp/print -m everywhere\n\n"
                else:
                    command = f"/System/Library/Printers/Libraries/ipp2ppd ipp://{ip}:631/ipp/print \"\" > {ppd_file}\n"
                    script.write(command)
                    command = f"lpadmin -p \"{desired_name}\" -L \"{desired_name}\" -o printer-is-shared=false -v {ip} -P {ppd_file}\n\n"
                script.write(command)
                increment += 1

        command = '# hdiutil create -volname Printers_Installer.app/ -srcfolder ~/Desktop/Printers_Installer.app  -ov -format UDZO "Printers_Installer.dmg"'
        script.write(command)
    
    print(f"Script '{script_file}' generated successfully!")

def main():
    parser = argparse.ArgumentParser(description="Generate printer installer script from CSV file")
    parser.add_argument("--csv", help="Path to the CSV file (default: printers.csv)", nargs='?', const="printers.csv")
    args = parser.parse_args()

    if args.csv:
        generate_installer_script(args.csv, 'printers-installer.sh')
    else:
        ippfind_output = run_command("ippfind")
        if ippfind_output:
            printers = ippfind_output.split('\n')
            printers_info = []
            for printer in printers:
                printer_name = printer.split('//')[1].split(':')[0]  # Extracting the hostname
                printer_ip = get_printer_ip(printer_name)
                if printer_ip:
                    # HP Printer Check
                    #curl -v --silent printer_ip --stderr - | grep userId | cut -d ">" -f 2 | sed -E 's/<[^>]+>//g; s/&nbsp;/_/g' | sed 's/_/ /' | awk '{sub(/___.*$/,"")} 1'
                    desired_name = run_command(f"curl -v --silent {printer_ip} --stderr - | grep userId | cut -d \">\" -f 2 | sed -E 's/<[^>]+>//g; s/&nbsp;/_/g' | sed 's/_/ /' | awk '{{sub(/___.*$/,\"\")}} 1' | sed 's/ /_/g' ")
                    if desired_name:
                        desired_name = desired_name.strip()
                        printers_info.append({'Desired_Name': desired_name, 'Hostname': printer_name, 'IP': printer_ip, 'Everywhere-Driver': 'yes'})
                    else:    
                        printers_info.append({'Desired_Name': '', 'Hostname': printer_name, 'IP': printer_ip, 'Everywhere-Driver': 'yes'})
                    print(f"Printer: {printer_name}, Label: {desired_name}, IP: {printer_ip}")
                else:
                    print(f"Failed to get IP for printer: {printer_name}")
            
            # Save to CSV file
            if printers_info:
                with open('printers.csv', 'w', newline='') as csvfile:
                    fieldnames = ['Desired_Name', 'Hostname', 'IP', 'Everywhere-Driver']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for printer_info in printers_info:
                            writer.writerow(printer_info)
        
        csv_file = 'printers.csv'
        script_file = 'printers-installer.sh'    
        generate_installer_script(csv_file, script_file)

if __name__ == "__main__":
    main()
