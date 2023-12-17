import struct
import os
import tkinter as tk
from tkinter import filedialog, simpledialog

class ISO9660Reader:
    """This class allows us to read ISO9660 files and extract data from those files.
    Users should enter a path to use it."""

    def __init__(self, iso_path):
        """Initialize the ISO9660Reader with the provided ISO path."""
        self.iso_path = iso_path
        self.volume_descriptor_size = 2048
        self.joliet_supplementary_size = 2048

    def show_volume_descriptor(self, offset):
        """Read and return the volume descriptor data at the specified offset."""
        with open(self.iso_path, 'rb') as iso_file:
            iso_file.seek(offset)
            raw_data = iso_file.read(struct.calcsize('>BB5s32sIHHHB32xQH'))
            descriptor = struct.unpack('>BB5s32sIHHHB32xQH', raw_data)
            return descriptor

    def parse_volume_descriptor(self):
        """Parse and display information from the volume descriptor."""
        standard_extent = self.show_volume_descriptor(16 * 2048)[8]
        joliet_extent = self.show_volume_descriptor(17 * 2048)[8]

        print("Volume Descriptor Data:")
        print("Joliet Extent:", joliet_extent)
        print("Standard Extent:", standard_extent)

        if joliet_extent != 0:
            return joliet_extent
        else:
            return standard_extent

    def read_directory_record(self, offset):
        """Read and return the directory record data at the specified offset."""
        with open(self.iso_path, 'rb') as iso_file:
            iso_file.seek(offset)
            raw_data = iso_file.read(struct.calcsize('>BBB7sII7sBB32s'))
            record = struct.unpack('>BBB7sII7sBB32s', raw_data)
            return record

    def parse_directory(self, extent):
        """Parse and return a list of directory records from the given extent."""
        records = []
        current_offset = extent

        while True:
            record = self.read_directory_record(current_offset)
            if record[0] == 0:
                break  # Terminator record

            records.append(record)
            current_offset += record[8]

        return records

    def list_contents(self, path=None):
        """List the contents of the specified directory or the root if no path is provided."""
        root_extent = self.parse_volume_descriptor()
        records = self.parse_directory(root_extent)

        if path:
            path = path.encode('utf-8')

            for record in records:
                if os.fsdecode(record[7]).encode('utf-8') == path:
                    if record[1] & 0x02:
                        print("Error: Specified path is not a directory.")
                        return
                    else:
                        directory_extent = record[10]
                        directory_records = self.parse_directory(directory_extent)
                        print(f"\nContents of directory '{path.decode('utf-8')}':")
                        for directory_record in directory_records:
                            print(os.fsdecode(directory_record[7]))
                    return
            print(f"Error: Path you provided '{path.decode('utf-8')}' can not be found.")
        else:
            print("\nEntire Directories and Files:")
            self.print_hierarchy(records)

    def print_hierarchy(self, records, indent=''):
        """Recursively print the directory hierarchy."""
        for record in records:
            if record[0] == 0x02:
                # Hidden directories won't be shown
                continue

            print(indent + os.fsdecode(record[7]))
            if record[1] & 0x02:
                directory_extent = record[10]
                directory_records = self.parse_directory(directory_extent)
                self.print_hierarchy(directory_records, indent + '  ')

    def extract_file(self, path):
        """Extract and display the content of the specified file."""
        root_extent = self.parse_volume_descriptor()
        records = self.parse_directory(root_extent)

        for record in records:
            if os.fsdecode(record[7]) == path:
                if record[1] & 0x02:
                    print("You must use list_contents function to view its contents.")
                    return
                else:
                    data_extent = record[10]
                    output_file_path = os.path.basename(path)
                    with open(self.iso_path, 'rb') as iso_file:
                        iso_file.seek(data_extent)
                        file_data = iso_file.read(record[4])
                        print(f"\nFile '{output_file_path}' content:")
                        print(file_data)
                    print(f"\nFile '{output_file_path}' extracted successfully.")
                    return
        print("Error: There is no such a file", path)
if __name__ == "__main__":
    # Create a simple Tkinter GUI for selecting the ISO file
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Prompt the user to select an ISO file
    iso_path = filedialog.askopenfilename(title="Select ISO File", filetypes=[("ISO Files", "*.iso")])

    if not iso_path:
        print("No file selected. Exiting.")
    else:
        print("Selected ISO Path:", iso_path)

        # Create an instance of ISO9660Reader with the selected ISO path
        iso_reader = ISO9660Reader(iso_path)

        # List all contents
        iso_reader.list_contents()

        # Prompt the user to select a specific path for listing contents
        path_for_listing = simpledialog.askstring("Enter Path for Listing", "Enter a path (or leave blank for root):")

        if path_for_listing:
            iso_reader.list_contents(path_for_listing)

        # Prompt the user to select a file path for extraction
        file_for_extraction = simpledialog.askstring("Enter File Path for Extraction", "Enter a file path for extraction:")

        if file_for_extraction:
            iso_reader.extract_file(file_for_extraction)