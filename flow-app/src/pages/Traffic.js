import Tab from "../components/Tab";

import "./traffic.css"
import TrafficFlow from "../components/TrafficFlow";
function Traffic() {
    return (
      <div>
        <Tab />
        <div className="box">
          <TrafficFlow />
        </div>
      </div>
    );
  }
  
  export default Traffic;
  