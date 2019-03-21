import json
import urllib3
import threading
import queue
import time
import sys

urllib3.disable_warnings()
block_num = None

class Node(threading.Thread):
    def __init__(self, url, queue):
        threading.Thread.__init__(self)
        self.block_num = None
        self.url = url
        self.queue = queue
        self.http = urllib3.PoolManager()

    # Perform API call to get block return None for non existing blocks and
    # any exceptions.
    def get_block(self):

        # API request
        PARAMS = {
            "jsonrpc": "2.0",
            "method": "block_api.get_block",
            "params": {"block_num": self.block_num},
            "id": 1
        }
        url = 'https://' + self.url

        try:
            # perform and decode request
            r = self.http.request('POST', url, body=json.dumps(PARAMS).encode())
            data = json.loads(r.data.decode())

            # Empty result for blocks that do not exist yet
            if len(data['result']) == 0:
                return (self.block_num, url, None)
            return (self.block_num, url, data)
        # retun None for any exceptions
        except Exception:
            return (self.block_num, url, None)

    def run(self):
        # global current block counter
        global block_num

        # check if the global block counter has been changed
        # if so retrieve block via api and put into queue
        while True:
            if block_num != self.block_num:
                self.block_num = block_num
                if block_num != None:
                    block = self.get_block()
                    self.queue.put(block)
            time.sleep(.1)

if __name__ == "__main__":
    # list of steem api nodes
    nodes = [
        'api.steemit.com',
        'api.steem.house',
        'appbasetest.timcliff.com',
        'rpc.steemviz.com',
        'steemd.privex.io',
        'rpc.usesteem.com',
    ]

    # threads list and queue object
    threads = []
    queue = queue.Queue()

    # create worker for each api, start and store
    for node in nodes:
        worker = Node(node, queue)
        worker.start()
        threads.append(worker)

    # set global block num
    block_num = int(sys.argv[1])

    while True:
        # when the queue reaches the same size as the amount of nodes
        # empty the queue
        if queue.qsize() == len(nodes):
            storage = []

            # Check if block has been retrieved successfully store if store
            for x in range(len(nodes)):
                block = queue.get()
                if block[2] != None:
                    storage.append(block)
                else:
                    print(block[1], block[0], 'Not valid')

            # Extract and compare block data
            data = [x[2] for x in storage]
            score = 0

            # Check block data against the first block that has been 
            # received. As this is non deterministic, in case of a corrupted
            # block, the order should be different when a retry is needed.
            for x in data[1:]:
                if x==data[0]:
                    score += 1

            # Calculate how many blocks are the same 
            final_score = (score+1)/len(nodes)

            print(f'Block: {block_num} Score: {final_score}')

            # When the score is higher than a certain treshhold go on to the
            # next block. If not reset the global block num. Wait for the workers 
            # to update and retry.
            if final_score > 0.75:
                block_num += 1
            else:
                temp = block_num
                block_num = None
                time.sleep(0.5)
                block_num = temp
        else:
            time.sleep(0.1)

