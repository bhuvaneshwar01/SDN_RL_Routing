import * as React from 'react';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import {useState,useEffect} from 'react';
import axios from "axios";

const columns = [
  {
    id: 'key',
    label: "S No.",
    minWidth:100,
    align: 'left',
    format: (value) => value.toLocaleString('en-US')
  },
  {
    id: 'src_node',
    label: "Source Switch Node",
    minWidth:170,
    align: 'left',
    format: (value) => value.toLocaleString('en-US')
  },
  {
    id: 'src_port',
    label: "Source Switch Port",
    minWidth:170,
    align: 'left',
    format: (value) => value.toLocaleString('en-US')
  },
  {
    id: 'dst_node',
    label: "Dst Switch Node",
    minWidth:170,
    align: 'left',
    format: (value) => value.toLocaleString('en-US')
  },
  {
    id: 'dst_port',
    label: "Dst Switch port",
    minWidth:170,
    align: 'left',
    format: (value) => value.toLocaleString('en-US')
  },
];

export default function Link_details() {
  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(10);
  const [rows,SetRows] = useState([]);

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(+event.target.value);
    setPage(0);
  };


  useEffect(() => {
    axios
      .get("http://127.0.0.1:5000/get_link_data")
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
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      <TableContainer sx={{ maxHeight: 440 }}>
        <Table stickyHeader aria-label="sticky table">
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align}
                  style={{ minWidth: column.minWidth }}
                >
                  {column.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} align="center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : (
              rows
                .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                .map((row) => {
                  return (
                    <TableRow hover role="checkbox" tabIndex={-1} key={row.code}>
                      {columns.map((column) => {
                        const value = row[column.id];
                        return (
                          <TableCell key={column.id} align={column.align}>
                            {column.format && typeof value === 'number'
                              ? column.format(value)
                              : value}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        rowsPerPageOptions={[10, 25, 100]}
        component="div"
        count={rows.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
    </Paper>
  );
}