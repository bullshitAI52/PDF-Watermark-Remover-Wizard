import binascii

hex_str = "bfecc0d6d1a7cfb0c4a7b7a8caa8"
try:
    data = binascii.unhexlify(hex_str)
    print(f"Hex: {hex_str}")
    print(f"GBK: {data.decode('gbk', errors='ignore')}")
    print(f"UTF-8: {data.decode('utf-8', errors='ignore')}")
except Exception as e:
    print(e)
    
hex_str2 = "a1aaa1aa" # From debug output
try:
    data = binascii.unhexlify(hex_str2)
    print(f"Hex2: {hex_str2}")
    print(f"GBK2: {data.decode('gbk', errors='ignore')}")
except: pass
