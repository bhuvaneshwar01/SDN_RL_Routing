import React from "react";
import Graph from "react-graph-vis";
import "./style.css";


const Node = (props) => {
  const path = props.path;

  const nodes = path.map((n) => {
    const index = path.indexOf(n);

    if(index !== -1 && index !== 0 && index !== path.length - 1){
      return {
        id: n.toString(),
        label: n.toString()
      };
      }
  });

  const node = nodes.filter((element) => {
    return element !== undefined;
  });

  const edges = path.map((n) => {
    const index = path.indexOf(n);
    if (index !== -1 &&  index < path.length - 1 && index !== 0 && index + 1 !== path.length - 1){
      const nextNode = path[index+1];
      return {
        from: n.toString(),
        to: nextNode.toString()
      };
    }
  });

  const edge = edges.filter((element) => {
    return element !== undefined;
  });

  console.log("Nodes ",node);
  console.log("Edges ",edge);

  const events = {
    select: function(event) {
      var { nodes, edges } = event;
    }
  };

  const graph = {
    nodes: node,
    edges: edge
  };

  const options = {
    layout: {
      hierarchical: false
    },
    edges: {
      color: "#000000"
    },
    nodes: {
      // shape: 'box',
      radius: 24,
      fontSize: 18,
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
    height: "200px"
  };    

  return(
  <div>
      <Graph
          graph={graph}
          events={events}
          options={options}
          getNetwork={network => {
            //  if you want access to vis.js network api you can set the state in a parent component using this property
          }} 
      />
  </div>);
};

export default Node;

// const Node = (props) => {
//   const [graph,setGraph] = useState({nodes: [], edges: []});
//   const [isLoading, setIsLoading] = useState(true);

//   const path = props.path;
//   console.log("Path : ",path)

//   const options = {
//     layout: {
//       hierarchical: false,
//       improvedLayout: false,
//       nodeSpacing: 1000
//     },
//     edges: {
//       color: "#000000",
//       length: 400
//     },
//     nodes: {
//       radius: 24,
//       fontSize: 18,
//       widthMin: 20,
//       widthMax: 20,
//       size: 50,
//       borderWidth: 2,
//       label: {
//         enabled: true,
//         font: {
//           size: 14
//         },
//         color: "black",
//         position: "inside"
//       }
//     }, 
//     height: "1000px",
//     // smoothCurves: false,
//     // stabilize: false,
//   };

//   const nodes = path.map((n) => {
//     return {
//       id: n.toString(),
//       label: n.toString()
//     }
//     setIsLoading(false);
//   });

//   setGraph({
//     nodes: nodes,
//     edges: [],
//   });

//   const events = {
//     select: function(event) {
//       var { nodes, edges } = event;
//     }
//   };

//   return (
//     {path}
//     // <div>
//     //   <p>{path}</p>
//       /* {isLoading ? (
//         <h2>Loading graph .....</h2>
//       ) : (
//         <Graph
//           graph={graph}
//           options={options}
//           events={events}
//           getNetwork={network => {
//             //  if you want access to vis.js network api you can set the state in a parent component using this property
//           }}
//         />
//       )}       }*/
//     // </div>
//   );
// }

// export default Node;
