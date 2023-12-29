import struct
import os
import tkinter as tk
from tkinter import filedialog, simpledialog


class ISOFileProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.descriptor_size = 2048
        self.supplementary_size = 2048

    def read_descriptor(self, offset):
        with open(self.file_path, 'rb') as file:
            file.seek(offset)
            raw_data = file.read(struct.calcsize('>BB5s32sIHHHB32xQH'))
            descriptor = struct.unpack('>BB5s32sIHHHB32xQH', raw_data)
            return descriptor

    def parse_descriptor(self):
        standard_extent = self.read_descriptor(16 * self.descriptor_size)[8]
        supplementary_extent = self.read_descriptor(17 * self.descriptor_size)[8]

        print("Descriptors:")
        print(f"Standard Extent: {standard_extent}")
        print(f"Supplementary Extent: {supplementary_extent}")

        if supplementary_extent != 0:
            return supplementary_extent
        else:
            return standard_extent

    def print_descriptor_info(self, label, descriptor):
        print(f"\n{label} Descriptor Info:")
        print(f"  Type: {descriptor[0]}")
        print(f"  Identifier: {descriptor[1]}")

        # Decode System Identifier as ASCII
        try:
            system_identifier = descriptor[2].decode('ascii').rstrip()
            print(f"  System Identifier: {system_identifier}")
        except UnicodeDecodeError:
            print("  System Identifier: (Unable to decode as ASCII)")

        # Decode Identifier as ASCII
        try:
            identifier = descriptor[3].decode('ascii').rstrip()
            print(f"  Identifier: {identifier}")
        except UnicodeDecodeError:
            print("  Identifier: (Unable to decode as ASCII)")

        # Handle Set Identifier as an integer
        if len(descriptor) > 9:
            print(f"  Set Identifier: {descriptor[9]}")

        # Check for the existence of the rest of the fields
        if len(descriptor) > 12:
            print(f"  Total LBA: {descriptor[4]}")
            print(f"  Block Size: {descriptor[5]}")
            print(f"  Table Size: {descriptor[6]}")
            print(f"  Table LBA: {descriptor[7]}")
            print(f"  Root Record: {descriptor[8]}")
            print(f"  Sequence Number: {descriptor[10]}")
            print(f"  Block Size (Optional): {descriptor[11]}")
            print(f"  Table Size (Optional): {descriptor[12]}")
        else:
            print("  (Additional fields not available)")

    def read_record(self, offset):
        with open(self.file_path, 'rb') as file:
            file.seek(offset)
            raw_data = file.read(struct.calcsize('>BBB7sII7sBB32s'))
            record = struct.unpack('>BBB7sII7sBB32s', raw_data)
            return record

    def parse_directory(self, extent):
        records = []
        current_offset = extent

        while True:
            record = self.read_record(current_offset)
            if record[0] == 0:
                break

            records.append(record)
            current_offset += record[8]

        return records

    def list_entries(self, path=None):
        root_extent = self.parse_descriptor()
        records = self.parse_directory(root_extent)
        print(path)
        if path:
            path = os.path.normpath(path)
            path = path.encode('utf-8')

            target_record = None
            for record in records:
                if record[7].decode('utf-8') == path:
                    target_record = record
                    break

            if not target_record:
                print(f"Error: Path '{os.fsdecode(path)}' not found.")
                return
            print(target_record)
            if target_record[1] & 0x02:
                directory_extent = target_record[10]
                directory_records = self.parse_directory(directory_extent)
                print(f"\nContents of directory '{os.fsdecode(path)}':")
                self.print_entries(directory_records, indent='  ')
            else:
                print(f"\nFile info for '{os.fsdecode(path)}':")
                print(f"    Size: {target_record[4]} bytes")
                print(f"    Data Extent: {target_record[10]}")
        else:
            print("\nAll Files and Directories:")
            self.print_entries(records)

    def print_entries(self, records, indent=''):
        for record in records:
            if record[0] == 0x02:
                continue
            entry_name = os.fsdecode(record[7]).strip('\0')
            if record[1] & 0x02:
                print(f"{indent}{entry_name} (directory)")
            else:
                print(f"{indent}{entry_name} (file)")

    def extract_data(self, path, destination=None):
        root_extent = self.parse_descriptor()
        records = self.parse_directory(root_extent)

        for record in records:
            if os.fsdecode(record[7]) == path:
                if record[1] & 0x02:
                    print("Error: Specified path is a directory. Use 'list_entries' to view its contents.")
                    return
                else:
                    data_extent = record[10]
                    if destination:
                        destination = os.path.normpath(destination)
                        destination_path = os.path.join(destination, os.path.basename(path))
                        with open(destination_path, 'wb') as output_file:
                            with open(self.file_path, 'rb') as file:
                                file.seek(data_extent)
                                data = file.read(record[4])
                                output_file.write(data)
                        print(f"\nFile '{str(path)}' extracted successfully to '{destination_path}'.")
                        return
                    else:
                        with open(self.file_path, 'rb') as file:
                            file.seek(data_extent)
                            data = file.read(record[4])
                            print(f"\nFile '{str(path)}' content:")
                            print(data)
                        return
        print(f"Error: File '{str(path)}' not found.")

        # Additional check to print a message for an empty destination folder
        if destination and not os.listdir(destination):
            print(f"Warning: Destination folder '{destination}' is empty.")
    @classmethod
    def select_file(cls):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(title="Select File", filetypes=[("ISO files", "*.iso")])

        if not file_path:
            print("No file selected. Exiting.")
            exit()

        print("Selected File Path:", file_path)
        return cls(file_path)


if __name__ == "__main__":
    processor = ISOFileProcessor.select_file()

    processor.print_descriptor_info("Standard", processor.read_descriptor(16 * processor.descriptor_size))
    processor.print_descriptor_info("Supplementary", processor.read_descriptor(17 * processor.descriptor_size))

    processor.list_entries("")

    processor.list_entries("")

    file_to_extract = ISOFileProcessor.select_file()
    destination_folder = filedialog.askdirectory(title="Select Destination Folder")

    processor.extract_data(path=file_to_extract, destination=destination_folder)

    print("File Path :",processor.file_path)

"""
 Window 1 : Select an ISO file
 Window 2 : Select an ISO file
 Window 3 : Select a directory to extract files
"""