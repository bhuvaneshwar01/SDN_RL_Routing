
import numpy as np
from scipy.stats import dirichlet
from sklearn.cluster import KMeans
import warnings
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


# Sample traffic data for demonstration purposes
# traffic_data = {
#     '10.0.0.1': {'pkts': [{'size': 100}, {'size': 150}, {'size': 200}], 'dst_ips': ['192.168.0.1', '192.168.0.2']},
#     '10.0.0.2': {'pkts': [{'size': 50}, {'size': 75}, {'size': 100}], 'dst_ips': ['192.168.0.1', '192.168.0.2', '192.168.0.3']},
#     '10.0.0.3': {'pkts': [{'size': 50}, {'size': 75}, {'size': 100}, {'size': 150}], 'dst_ips': ['192.168.0.2']}
# }
def bot_detection(traffic_data):
    # Aggregate the traffic data by source IP address
    agg_data = {}
    for src_ip, data in traffic_data.items():
        pkt_sizes = [pkt for pkt in data['pkts']]
        agg_data[src_ip] = {'pkt_count': len(pkt_sizes),
                            'total_bytes': sum(pkt_sizes),
                            'dst_ips': list(set(data['dst_ips'])),
                            'pkt_sizes': pkt_sizes}

    # Calculate the Dirichlet distribution for each source IP address
    dirichlet_data = {}
    for src_ip, data in agg_data.items():
        alpha = [1] * (max(data['pkt_sizes']) + 1)  # use a uniform prior
        alpha += np.bincount(data['pkt_sizes'])  # add the observed counts
        dirichlet_dist = dirichlet(alpha)
        dirichlet_data[src_ip] = {'alpha': alpha,
                                'dist': dirichlet_dist}

    # Calculate the probability density function for each packet size for each source IP address
    pdf_data = {}
    for src_ip, data in agg_data.items():
        dirichlet_dist = dirichlet_data[src_ip]['dist']
        pkt_sizes = np.bincount(data['pkt_sizes'])
        pdf = dirichlet_dist.pdf(pkt_sizes / np.sum(pkt_sizes))
        pdf_data[src_ip] = {'pdf': pdf}

    # print(pdf_data)

    # Calculate the consistency score for each source IP address
    const_data = {}
    for src_ip, data in agg_data.items():
        pkt_count = data['pkt_count']
        total_bytes = data['total_bytes']
        dst_ips = data['dst_ips']
        dst_count = len(dst_ips)
        const_score = pkt_count / dst_count
        pkt_sizes = data['pkt_sizes']  # add this line
        const_data[src_ip] = {'pkt_count': pkt_count,
                            'total_bytes': total_bytes,
                            'dst_count': dst_count,
                            'const_score': const_score,
                            'pkt_sizes': pkt_sizes}  # add 'pkt_sizes' key

    # print("const data : " + str(const_data))

    # Cluster the source IP addresses based on the consistency score and the PDF of packet sizes
    X = []
    for src_ip, const in const_data.items():
        if src_ip in pdf_data:
            pdf = pdf_data[src_ip]['pdf']
            pkt_sizes = const['pkt_sizes']
            pdf_values = [pdf.get(pkt_size, 0) if isinstance(pdf, dict) else 0 for pkt_size in pkt_sizes]
            pdf_mean = sum(pdf_values) / len(pdf_values) if len(pdf_values) > 0 else 0
            X.append([const['pkt_count'],const['dst_count'],const['const_score'], pdf_mean])
    X = np.array(X)


    kmeans = KMeans(n_clusters=2, random_state=0).fit(X)
    labels = kmeans.labels_

    # Label each cluster as "normal" or "bot"
    normal_cluster = 0 if np.mean(labels) < 0.5 else 1
    bot_cluster = 1 - normal_cluster
    for i, src_ip in enumerate(agg_data.keys()):
        cluster = labels[i]
        if cluster == normal_cluster:
            cluster_label = 'normal'
        else:
            if np.sum(pdf_data[src_ip]['pdf'] > 0.1) > 3 or const_data[src_ip]['const_score'] < 0.5 or const_data[src_ip]['pkt_count'] >= 50:
                cluster_label = 'bot'
            else:
                cluster_label = 'normal'
        agg_data[src_ip]['cluster'] = cluster_label

    # for src_ip,data in agg_data.items():
    #     if data['pkt_count'] >= 100:
    #         agg_data[src_ip]['cluster'] = 'bot'

    print("\t[+]\tAgg data : " + str(agg_data))
    # print("\n pdf : "+str(pdf_data))
    # Use the labeled clusters to detect and block bot traffic in real-time
    for src_ip, data in agg_data.items():
        if data['cluster'] == 'bot':
            print("************BOT DETECTION : " + str(src_ip))
    
    return agg_data

# print(bot_detection(traffic_data=traffic_data))