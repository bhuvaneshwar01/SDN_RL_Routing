import './App.css';
import {Route,Routes} from 'react-router-dom';

import Details from './pages/details';
import Traffic from './pages/Traffic';
import Graph from './pages/Graph';

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path='/' element={<Graph />} />
        <Route path='/graph' element={<Graph />} />
        <Route path='/traffic' element={<Traffic />} />
        <Route path='/details' element={<Details />} />
      </Routes>
    </div>
  );
}

export default App;
