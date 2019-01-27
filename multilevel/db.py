from pymodm import connect, MongoModel, fields
import pickle, pymongo
from bson.objectid import ObjectId
from .utils import absoluteFilePaths, fpath
from .parsers import GMLParser, GMLParserDB, parseNetworkData
from .basic import mkLayout, mkMetaNetwork

class Connection:
    def __init__(self):
        mclient = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = mclient['boilerplate']
        # the networks collection keeps both uncoarsened and coarsened networks
        # a layer is a network with specific layer number and coarsening method
        # layer == 0 for the original (uncoarsened) network
        self.networks = self.db['networks']
        # any network may have a layout given by the network _id and the layout method
        self.layouts = self.db['layouts']

    def getNetLayer(self, netid, method, layer):
        if layer > 0:
            query = {'uncoarsened_network': ObjectId(netid), 'layer': layer, 'coarsen_method': method}
        else:
            query = {'uncoarsened_network': ObjectId(netid), 'layer': layer}
        network_ = self.networks.find_one(query)
        print(query, 'QUERY')
        if network_:
            network = parseNetworkData(network_)
        else:
            if layer - 1 > 0:
                query = {'uncoarsened_network': ObjectId(netid), 'layer': layer - 1, 'coarsen_method': method}
            else:
                query = {'uncoarsened_network': ObjectId(netid), 'layer': layer - 1}
            previous_network_ = self.networks.find_one(query)
            previous_network = parseNetworkData(previous_network_)
            network = mkMetaNetwork(previous_network, method)
            self.networks.insert_one({
                'data': pickle.dumps(network),
                'uncoarsened_network': ObjectId(netid),
                'coarsen_method': method,
                'layer': layer,
                'filename': previous_network_['filename']
            })
        return network

    def getNetLayout(self, netid, method, layer, layout, dimensions, network):
        # find _id of network from netid, method, layer
        # find layout. Make and write it if not available
        if layer > 0:
            query = {'uncoarsened_network': ObjectId(netid), 'layer': layer, 'coarsen_method': method}
        else:
            query = {'uncoarsened_network': ObjectId(netid), 'layer': layer}
        network_id = self.networks.find_one(query, {'_id': 1})
        query2 = {'network': network_id['_id'], 'layout_name': layout, 'dimensions': dimensions}
        layout_ = self.layouts.find_one(query2)
        if layout_:
            positions = pickle.loads(layout_['data'])
        else:
            positions = mkLayout(netid, method, layout, dimensions, layer, network)
            self.layouts.insert_one({
                'data': pickle.dumps(positions),
                'network': network_id['_id'],
                'layout_name': layout,
                'dimensions': dimensions
            })
        return positions


    def getNet(self, netid):
        query = {'_id': ObjectId(netid)}
        print(query)
        network_ = self.networks.find_one(query)
        print(network_)
        network = GMLParserDB(network_['data']).g
        return network




### Deprecated:
class Network(MongoModel):
    network = fields.BinaryField()
    filename = fields.CharField()
    def save(self, cascade=None, full_clean=True, force_insert=False):
        self.network = pickle.dumps(self.network)
        return super(Network, self).save(cascade, full_clean, force_insert)

class MongoConnect:
    def connect(self):
        self.connect = connect('mongodb://localhost:27017/multilevelDatabase')
    def clear(self):
        Network.objects.delete()

class PopulateNetworks:
    def populate(self):
        self.getFilenames()
        self.getFilenames2()
        self.addToDB()
    def addToDB(self):
        nets = [Network(GMLParser(i).g, i).save() for i in self.fnames_]
        # Network.object.bulk_create(nets)
    def getFilenames(self, adir='/home/renato/Dropbox/Public/doc/vaquinha/'):
        self.fnames = absoluteFilePaths(adir)
        self.fnames_ = [i for i in self.fnames if i.endswith('.gml')]
    def getFilenames2(self, adir='/home/renato/Dropbox/Public/doc/avlab/'):
        self.fnames = absoluteFilePaths(adir)
        self.fnames_ += [i for i in self.fnames if i.endswith('.gml')]

