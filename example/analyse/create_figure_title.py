import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import networkx as nx

def create_figure_title(param, data_1, image=None, alpha_image=0.4, threshold=1.0, size_edges=1.0, color_Nest='royalblue', color_TVB='tomato',
                       size_node_TVB=50.0, size_node_Nest=100.0, alpha_node=1.0, size_neurons=0.1):
    """
    print three figure and some text about the connectome for the simulation
    :param param: parameter for the simulation
    # parameter for display the graph (only available if the centers of regions is available)
    # parameter for the background image
    :param image: the image to ad in background of the graph
    :param alpha_image: the transparency of the image
    # parameter for edge of the graph
    :param threshold: the threshold for the plotting edge of the connectome
    :param size_edges: size of the line of the edges
    # parameter for nodes of the graph
    :param color_Nest: the color of node simulate with Nest
    :param color_TVB: the color of node simulate with TVB
    :param size_node_TVB: the size of the node simulate with TVB
    :param size_node_Nest: the size of the node simulate with Nest
    :param alpha_node: the transparency of the node
    :return:
    """
    weights = np.load(param['param_nest_connection']["path_weight"])
    weights[np.where(weights == 0.0)] = np.NAN
    delays = np.load(param['param_nest_connection']["path_distance"]) / param['param_nest_connection']["velocity"]
    ids = param['param_co_simulation']["id_region_nest"]
    nb_regions = param['param_nest_topology']["nb_region"]

    # plot 2d connectome
    # get position of the node
    centres = np.loadtxt(param['param_tvb_connection']['path_centers'])
    Nposition = np.swapaxes(centres[:2, :], 0, 1)
    # select edges to show
    weights_threshold = weights
    weights_threshold[np.where(weights_threshold < threshold)] = 0.0
    # select the color for the nodes
    color_nodes = [color_TVB for i in range(nb_regions)]
    for id in ids:
        color_nodes[id] = color_Nest
    # select the size of the nodes
    size_nodes = np.array([size_node_TVB for i in range(nb_regions)])
    size_nodes[ids] = size_node_Nest

    # create the graph and print it
    fig = plt.subplot(121)
    ax = plt.gca()
    G = nx.from_numpy_matrix(weights_threshold)
    nx.draw(G, width=size_edges, pos=Nposition, edge_color='#909089', ax=ax, node_color=color_nodes,
            node_size=size_nodes,
            node_shape='o', alpha=alpha_node)
    # display an image if one is give (change perhaps the format)
    if image is not None:
        image = np.load(image)
        plt.imshow(image, cmap='gray', vmin=image.min(), vmax=image.max(), alpha=alpha_image)
        plt.xlim(xmax=image.shape[1], xmin=0)
        plt.ylim(ymax=image.shape[0], ymin=0)
    else:
        plt.xlim(xmax=np.max(Nposition[:, 0]) + 0.1, xmin=np.min(Nposition[:, 0]) - 0.1)
        plt.ylim(ymax=np.max(Nposition[:, 1]) + 0.1, ymin=np.min(Nposition[:, 1]) - 0.1)

    plt.subplot(143)
    times = result_raw[0]
    state_variable = np.concatenate(result_raw[1]).reshape((result_raw[1].shape[0], 7, nb_regions))  # shape : time, state variable, region
    for id in ids:
        state_variable[:,0,id] /=2
    max_rate_E = np.nanmax(state_variable[:, 0, :]) * 1e3 +10.0
    for i in range(int(nb_regions)):
        plt.plot(times, state_variable[:, 0, i] * 1e3 + i * max_rate_E, color=color_TVB)
    for i in ids:
        plt.gca().lines[i].set_color(color_Nest)
    plt.axis('off')


    spikes_ex = data['pop_1_ex']
    spikes_in = data['pop_1_in']
    plt.subplot(244)
    for i in range(spikes_ex[0].shape[0]):
        plt.plot(spikes_ex[1][i], np.repeat(spikes_ex[0][i], spikes_ex[1][i].shape[0]), '.b',
             markersize=size_neurons)
    for i in range(spikes_in[0].shape[0]):
        plt.plot(spikes_in[1][i], np.repeat(spikes_in[0][i], spikes_in[1][i].shape[0]), '.r',
                 markersize=size_neurons)
    plt.axis('off')

    spikes_ex = data['pop_2_ex']
    spikes_in = data['pop_2_in']
    plt.subplot(248)
    for i in range(spikes_ex[0].shape[0]):
        plt.plot(spikes_ex[1][i], np.repeat(spikes_ex[0][i], spikes_ex[1][i].shape[0]), '.b',
             markersize=size_neurons)
    for i in range(spikes_in[0].shape[0]):
        plt.plot(spikes_in[1][i], np.repeat(spikes_in[0][i], spikes_in[1][i].shape[0]), '.r',
                 markersize=size_neurons)
    plt.axis('off')



    plt.show()
# Test the function, helping for debugging
if __name__ == '__main__':
    from example.analyse.get_data import get_data_all,get_rate
    param = { 'param_nest_connection':{"path_weight":'/home/kusch/Documents/project/co_simulation/TVB-NEST/example/parameter/data_mouse/weights.npy',
                                       "path_distance": '/home/kusch/Documents/project/co_simulation/TVB-NEST/example/parameter/data_mouse/distance.npy',
                                        "velocity":3.0},
              'param_co_simulation':{"id_region_nest":[29,81]},
              'param_nest_topology':{"nb_region":104},
              'param_tvb_connection':{'path_region_labels':'/home/kusch/Documents/project/co_simulation/TVB-NEST/example/parameter/data_mouse/region_labels.txt',
                                      'path_centers':'/home/kusch/Documents/project/co_simulation/TVB-NEST/example/parameter/data_mouse/centres.txt'
                                      }
              }
    # color_Nest = 'royalblue'
    # color_TVB  = 'tomato'
    # color_Nest = 'darkviolet'
    color_Nest = 'gold'
    # color_TVB  = 'darkturquoise'
    # color_TVB  = 'lightseagreen'
    # color_TVB  = 'mediumturquoise'
    color_TVB  = 'darkgreen'

    data = get_data_all('/home/kusch/Documents/project/co_simulation/co-simulation-tvb-nest/example/test_sim_2/nest/')
    result_raw = get_rate('/home/kusch/Documents/project/co_simulation/co-simulation-tvb-nest/example/test_sim_2/tvb/')[0]  # result of the Raw monitor

    create_figure_title(param, data, image='/home/kusch/Documents/project/co_simulation/TVB-NEST/example/parameter/data_mouse/StruturalMRI_allen_40.npy',
                       color_Nest=color_Nest, color_TVB=color_TVB,
                       size_edges=0.5,
                       threshold=0.05, size_neurons=0.1)