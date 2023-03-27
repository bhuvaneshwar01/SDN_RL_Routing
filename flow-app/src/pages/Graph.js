import * as React from 'react';
import './graph.css';

import Tab from '../components/Tab';
import Grph from '../components/createGraph'
function Graph() {
  return (
    <div>
      <Tab />
      <div className='box'>
        <Grph />
      </div>
    </div>
  );
}

export default Graph;
