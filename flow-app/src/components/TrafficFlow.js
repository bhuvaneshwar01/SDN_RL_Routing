import * as React from 'react';
import { styled } from '@mui/material/styles';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell, { tableCellClasses } from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import axios from 'axios';
import {useState,useEffect} from 'react';

import Node from './Node';

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.${tableCellClasses.head}`]: {
    backgroundColor: theme.palette.common.black,
    color: theme.palette.common.white,
  },
  [`&.${tableCellClasses.body}`]: {
    fontSize: 14,
  },
}));

const StyledTableRow = styled(TableRow)(({ theme }) => ({
  '&:nth-of-type(odd)': {
    backgroundColor: theme.palette.action.hover,
  },
  // hide last border
  '&:last-child td, &:last-child th': {
    border: 0,
  },
}));

function createData(name, calories, fat, carbs, protein) {
  return { name, calories, fat, carbs, protein };
}


export default function TrafficFlow() {
  const [rows,setRows] = useState([]);

  useEffect(() => {
    axios
      .get("http://127.0.0.1:5000/traffic_flow_data")
      .then((res) => {
        const setList = res.data;
        setRows(setList);
        console.log("List : ",setList)
      })
      .catch((error) => {
        console.log("Error ", error);
      });

  }, []);

  return (
    <TableContainer component={Paper}>
      <Table sx={{ minWidth: 700 }} aria-label="customized table">
        <TableHead>
          <TableRow>
            <StyledTableCell>S No.</StyledTableCell>
            <StyledTableCell>Src MAC Address</StyledTableCell>
            <StyledTableCell>Src IP Address</StyledTableCell>
            <StyledTableCell>Dst MAC Address</StyledTableCell>
            <StyledTableCell>Dst IP Address</StyledTableCell>
            <StyledTableCell>Packet Type</StyledTableCell>
            <StyledTableCell>Packet Size</StyledTableCell>
            <StyledTableCell>Path</StyledTableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <StyledTableRow key={row.key}>
              <StyledTableCell >{row.key}</StyledTableCell>
              <StyledTableCell >{row.src_mac}</StyledTableCell>
              <StyledTableCell >{row.src_ip}</StyledTableCell>
              <StyledTableCell >{row.dst_mac}</StyledTableCell>
              <StyledTableCell >{row.dst_ip}</StyledTableCell>
              <StyledTableCell >{row.pkt_type}</StyledTableCell>
              <StyledTableCell >{row.pkt_size}</StyledTableCell>
              <StyledTableCell >
                  <Node path={row.path} />
              </StyledTableCell>
            </StyledTableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
