import * as React from 'react';

import Tab from '../components/Tab';
import Grph from '../components/createGraph'
function Graph() {
  return (
    <div>
      <Tab />
      <div>
        <Grph />
      </div>
    </div>
  );
}

export default Graph;
