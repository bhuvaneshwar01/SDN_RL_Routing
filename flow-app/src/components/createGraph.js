import React from "react";
import ReactDOM from "react-dom";
import Graph from "react-graph-vis";
import axios from "axios";
import {useState,useEffect} from "react";

function Grph() {
  const [node, setNode] = useState([])
  const [link,setLink] = useState([])
  const [graph,setGraph] = useState({nodes: [], edges: []});
  const [isLoading, setIsLoading] = useState(true);

  
  useEffect(() => {
    axios
      .get("http://127.0.0.1:5000/get_switch_node")
      .then((res) => {
        const nodes = res.data["py/set"].map((n) => {
          return {
            id: n.toString(),
            label: "Node " + n.toString(),
            image: "",
          };
        });

        nodes.forEach(node => {
          console.log(node ," -> ",/:/g.test(node.id));
          if(node.image == ""){
            node.image = "/images/hub.png";
          }
          if((/:/g.test(node.id))){
            node.image = "/images/desktop.png";
          }
          
        });

        setNode(nodes);
        console.log("Node ", nodes);
        setIsLoading(false);
      })
      .catch((error) => {
        console.log("Error ", error);
        setIsLoading(false);
      });
    axios
      .get("http://127.0.0.1:5000/get_switch_link")
      .then((res) => {
        const setList = res.data["py/set"];

        // const e = setList.map((set) => console.log("l ",set["py/tuple"]));

        const edgesList = setList.map((set) => ({
          from: set["py/tuple"][0].toString(),
          to: set["py/tuple"][1].toString(),
        }));
        setLink(edgesList);
        console.log("Link ", edgesList);

        setIsLoading(false);
      })
      .catch((error) => {
        console.log("Error ", error);
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    setGraph({
      nodes: node,
      edges: link,
    });

    console.log("Graph " ,graph)
  }, [node, link]);


  const options = {
    layout: {
      hierarchical: false,
      improvedLayout: false,
      nodeSpacing: 1000
    },
    edges: {
      color: "#000000",
      length: 400
    },
    nodes: {
      shape: 'image',
      radius: 24,
      fontSize: 18,
      widthMin: 20,
      widthMax: 20,
      size: 50,
      borderWidth: 2,
      label: {
        enabled: true,
        font: {
          size: 14
        },
        color: "black",
        position: "inside"
      }
    },
    physics: {
      // Even though it's disabled the options still apply to network.stabilize().
      enabled: true,
      solver: "repulsion",
      repulsion: {
        nodeDistance: 150 // Put more distance between the nodes.
      }
    },  
    shapeProperties: {
      useBorderWithImage: true,
      borderRadius: 50 // half of the size
    },
    height: "1000px",
    // smoothCurves: false,
    // stabilize: false,
  };

  const events = {
    select: function(event) {
      var { nodes, edges } = event;
    }
  };

  return (
    <div>
      {isLoading ? (
        <h2>Loading graph .....</h2>
      ) : (
        <Graph
          graph={graph}
          options={options}
          events={events}
          getNetwork={network => {
            //  if you want access to vis.js network api you can set the state in a parent component using this property
          }}
        />
      )}
    </div>
  );
}

export default Grph;
