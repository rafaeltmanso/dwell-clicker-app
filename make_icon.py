"""Generate a simple 32x32 app icon (.ico) for Dwell Clicker."""
import struct
import sys


def make_ico(path: str) -> None:
    size = 32
    bpp = 32
    # Row stride: ((width * bpp + 31) // 32) * 4
    row_stride = ((size * bpp + 31) // 32) * 4
    and_stride = ((size + 31) // 32) * 4

    xor_data = bytearray()
    cx, cy = size // 2, size // 2
    r_outer = 14
    r_inner = 9

    for y in range(size):
        row = bytearray()
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= r_inner:
                # filled center = dark
                row.extend((0x20, 0x10, 0x0b, 0xff))  # BGRA #0b1020
            elif dist <= r_outer:
                # ring = accent blue
                row.extend((0xed, 0x80, 0x2f, 0xff))  # BGRA #2f80ed
            else:
                # transparent
                row.extend((0x00, 0x00, 0x00, 0x00))
        while len(row) < row_stride:
            row.extend(b'\x00')
        xor_data.extend(row)

    and_data = bytearray(and_stride * size)
    data = bytes(xor_data) + bytes(and_data)

    ico_header = struct.pack('<HHH', 0, 1, 1)
    data_offset = 6 + 16
    directory = struct.pack(
        '<BBBBHHII',
        size, size, 0, 0, 1, bpp, len(data), data_offset,
    )

    with open(path, 'wb') as f:
        f.write(ico_header)
        f.write(directory)
        f.write(data)

    print(f"Icon saved: {path} ({6 + 16 + len(data)} bytes)")


if __name__ == "__main__":
    make_ico(sys.argv[1] if len(sys.argv) > 1 else "app.ico")
