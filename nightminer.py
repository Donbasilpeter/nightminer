import socket
import json
import hashlib
import binascii
from pprint import pprint
import time
import random

address = '1GvSP13YjQAu9VAa8J1Hvbc4n3N8kUE3Ch'
nonce = hex(random.randint(0, 2**32 - 1))[2:].zfill(8)

host = 'btc.f2pool.com'
port = 1314

print(f"address: {address} nonce: {nonce}")
print(f"host: {host} port: {port}")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

# Server connection
sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
response = json.loads(sock.recv(1024).decode('utf-8'))
sub_details, extranonce1, extranonce2_size = response['result']

# Authorize workers
sock.sendall(b'{"params": ["donbasilpeter.pyminer", "123123"], "id": 2, "method": "mining.authorize"}\n')

# Read 4 lines of response
response = ''
while response.count('\n') < 4:
    response += sock.recv(1024).decode('utf-8')

# Get rid of empty lines
responses = [json.loads(res) for res in response.split('\n') if res.strip()]

pprint(responses)

# Parse job parameters
job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = responses[2]['params']

# Calculate target
# Reference: http://stackoverflow.com/a/22161019
target = (nbits[2:] + '00' * (int(nbits[:2], 16))).zfill(64)
print(f'target: {target}\n')

extranonce2 = '00' * extranonce2_size

# Coinbase transaction
coinbase = coinb1 + extranonce1 + extranonce2 + coinb2
coinbase_hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(coinbase)).digest()).digest()

print(f'coinbase:\n{coinbase}\n\ncoinbase hash: {binascii.hexlify(coinbase_hash_bin).decode()}\n')

# Calculate Merkle root
merkle_root = coinbase_hash_bin
for h in merkle_branch:
    merkle_root = hashlib.sha256(hashlib.sha256(merkle_root + binascii.unhexlify(h)).digest()).digest()

merkle_root = binascii.hexlify(merkle_root).decode()

# Convert to little-endian
merkle_root = ''.join([merkle_root[i] + merkle_root[i + 1] for i in range(0, len(merkle_root), 2)][::-1])

print(f'merkle_root: {merkle_root}\n')

# Construct block header
blockheader = (
    version + prevhash + merkle_root + nbits + ntime + nonce +
    '000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000'
)

print(f'blockheader:\n{blockheader}\n')

# Double SHA256 hash
hash = hashlib.sha256(hashlib.sha256(binascii.unhexlify(blockheader)).digest()).digest()
hash = binascii.hexlify(hash).decode()
print(f'hash: {hash}')

if hash < target:
    print('success!!')
    payload = (
        '{"params": ["' + address + '", "' + job_id + '", "' + extranonce2 + '", "' + ntime + '", "' + nonce + '"], '
        '"id": 1, "method": "mining.submit"}\n'
    )
    sock.sendall(payload.encode('utf-8'))
    print(sock.recv(1024).decode('utf-8'))
else:
    print('failed mine, hash is greater than target')

sock.close()
