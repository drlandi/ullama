import os

def search_file(path, key):
    file_size = os.path.getsize(path)
    if file_size == 0:
        return -1

    num_records = file_size // 24
    left, right = 0, num_records - 1

    with open(path, 'rb') as f:
        while left <= right:
            mid = left + (right - left) // 2
            f.seek(mid * 24)
            current_key = int.from_bytes(f.read(8), 'big')

            if current_key == key:
                return mid
            elif current_key < key:
                left = mid + 1
            else:
                right = mid - 1

    return -1
