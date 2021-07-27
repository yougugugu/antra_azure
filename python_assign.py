from typing import Set, Tuple, Any
import re
import csv
import json
from azure.storage.blob import ContainerClient

### Question1

def handle_data(path: str) -> Set[Tuple[Any]]:
	'''
	Read data from given path and return data as a set.
	Param
		path: the path of file.
	Returns: 
		A set of data from file.
	'''
	result = set()
	with open(path, 'r') as f:
		lines = f.readlines()[1:]
		for line in lines:	
			first, last, email, phone, address = line.strip().split('\t')
			result.add((first.lower(), last.lower(), email.lower(), re.sub('-', '', phone), re.sub('no.|#', '', address.lower())))
	return result

p1 = handle_data('people_1.txt')
p2 = handle_data('people_2.txt')

with open('people.csv', 'w') as csvfile:
	wr = csv.writer(csvfile, delimiter = ',')
	wr.writerow(['FirstName', 'LastName', 'Email', 'Phone', 'Address'])
	for line in p1.union(p2):
		wr.writerow(line)



### Question2

with open('movie.json', 'r', encoding='utf8') as f:
	y = json.load(f)

cnt = len(y['movie'])


for i in range(8):
	with open('movie_' + str(i) + '.json', 'w', encoding='utf-8') as f:
		json.dump({'movie': y['movie'][int(cnt * (i / 8)) : int(cnt * (i + 1 / 8))]}, f)



### Question3

connection_string = '''
DefaultEndpointsProtocol=https;AccountName=antrablobstorage;AccountKey=E
CVP9sDWl64Ubd6w3lGd4d4fbiZuwHWWu1q/KoS2sCR18mwwkSxf1gLC7PvqC
T1jWi3IYE87ZQtJYMIztIg3vg==;EndpointSuffix=core.windows.net'''

container_name = 'imagescontainer'

container = ContainerClient.from_connection_string(conn_str = connection_string, container_name = container_name)

blob_list = container.list_blobs()

for blob in blob_list:
	print('{:<100}{:<10}  {:<10}'.format(blob.name, blob.blob_type, blob.size), end = '\n')
