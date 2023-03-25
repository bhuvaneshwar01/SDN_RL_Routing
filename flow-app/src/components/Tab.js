import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';

function CollapsibleExample() {
  return (
    <Navbar bg="dark" variant="dark">
        <Container>
          <Navbar.Brand href="#home">Flowmanager</Navbar.Brand>
          <Nav className="me-auto">
            <Nav.Link href="/">Graph</Nav.Link>
            <Nav.Link href="/traffic">Traffic data</Nav.Link>
            <Nav.Link href="/details">Detailed Information</Nav.Link>
          </Nav>
        </Container>
      </Navbar>
  );
}

export default CollapsibleExample;