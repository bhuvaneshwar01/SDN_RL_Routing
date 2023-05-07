import Tab from "../components/Tab";
import React from "react";
import {
  MDBCard,
  MDBCardBody,
  MDBCardTitle,
  MDBCardText,
  MDBRow,
  MDBCol,
  MDBBtn,
} from "mdb-react-ui-kit";
import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';

import './detail.css'
import Host_details from "../components/host_details";
import Link_details from "../components/link_details";
import Bot_tables from "../components/bot_details";
import Path_tables from "../components/path";

const Item = styled(Paper)(({ theme }) => ({
  backgroundColor: theme.palette.mode === 'dark' ? '#1A2027' : '#fff',
  ...theme.typography.body2,
  padding: theme.spacing(1),
  textAlign: 'center',
  color: theme.palette.text.secondary,
}));


function Details() {
  return (
    <div>
      <Tab />
      {/* host and link details */}
      <div className="box">
        <MDBRow>
          <MDBCol sm="6">
            <MDBCard>
              <MDBCardBody>
                <MDBCardTitle>Host Details</MDBCardTitle>
                <MDBCardText>
                  <Host_details />
                </MDBCardText>
              </MDBCardBody>
            </MDBCard>
          </MDBCol>
          <MDBCol sm="6">
            <MDBCard>
              <MDBCardBody>
                <MDBCardTitle>Link details</MDBCardTitle>
                <MDBCardText>
                 <Link_details />
                </MDBCardText>
              </MDBCardBody>
            </MDBCard>
          </MDBCol>
        </MDBRow>
      </div>
    </div>
  );
}

export default Details;
