import * as React from 'react';
import { styled } from '@mui/material/styles';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell, { tableCellClasses } from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import {useState,useEffect} from 'react';
import axios from "axios";

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



export default function Bot_tables() {
  const [rows,SetRows] = useState([]);
  useEffect(() => {
    axios
      .get("http://127.0.0.1:5000/get_bot")
      .then((res) => {
        const setList = res.data;
        const arr = Object.keys(setList).map((key) => {
          const obj = setList[key]
          return {key, ...obj};
        })

        const r = [...arr]
        SetRows(r);

        console.log(rows) 
        
      })
      .catch((error) => {
        console.log("Error ", error);
      });

  }, []);
  
  return (
    <div>
    {rows.length === 0 ? (
      <h4> No Bot Found</h4>
    ) : (
      <TableContainer component={Paper}>
      <Table sx={{ minWidth: 250 }} aria-label="customized table">
        <TableHead>
          <TableRow>
            <StyledTableCell>S No</StyledTableCell>
            <StyledTableCell >IP Address</StyledTableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <StyledTableRow key={row.key}>
              <StyledTableCell component="th" scope="row">
                {row.key}
              </StyledTableCell>
              <StyledTableCell >{row.ip_address}</StyledTableCell>
            </StyledTableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>    
  )}
  </div>
  );
}