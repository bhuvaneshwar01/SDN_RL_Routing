import React from 'react';
import "./style.css";


const Node = (props) => {
  return (
    <div>
      <img src={props.image} alt="Node Image" />
      <h2>{props.title}</h2>
      <p>{props.description}</p>
    </div>
  );
}

export default Node;
