import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import axios from 'axios';
import { useEffect } from 'react';

function onHandleClear() {
  // useEffect(() => {
    axios
      .get(" http://127.0.0.1:5000/truncate")
      .then((res) => {
        console.log("done")        
      })
      .catch((error) => {
        console.log("Error ", error);
      });

  // }, []);

};
function CollapsibleExample() {
  return (
    <Navbar bg="dark" variant="dark">
        <Container>
          <Navbar.Brand href="#home">Flowmanager</Navbar.Brand>
          <Nav className="me-auto">
            <Nav.Link href="/">Graph</Nav.Link>
            <Nav.Link href="/traffic">Traffic data</Nav.Link>
            <Nav.Link href="/details">Detailed Information</Nav.Link>

            {/* <button onClick={onHandleClear()}> Clear</button> */}
          </Nav>
        </Container>
      </Navbar>
  );
}

export default CollapsibleExample;