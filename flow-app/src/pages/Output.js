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


function Output() {
  return (
    <div>
      <Tab />
      {/* host and link details */}
      <div className="box">
      <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        <Grid item xs={8}>
          <Item>
          <h2>BOT DETECTION</h2>
        <p>  The Dirichlet model is a statistical approach used for detecting bots by analyzing the frequency distribution of words in their messages. The model assigns probabilities to the occurrence of different words in a message, and it can detect bots by identifying patterns of word usage that are inconsistent with those of human users. Additionally, aggregated and consistency behavior analysis involves examining patterns in the bot's behavior such as the time between messages, the types of content posted, and the sources of the messages. This approach can identify bots that behave in a consistent and repetitive manner. Finally, K-means clustering is a machine learning algorithm that can group similar bots together based on their behavior and patterns of communication. By analyzing the behavior of bots and comparing it to that of human users, these techniques can help identify and mitigate the effects of bots in online communities. </p>
          </Item>
        </Grid>
        <Grid item xs={4}>
          <Item>
            <Bot_tables />
          </Item>
        </Grid>
      </Grid>
    </Box>
      </div>
      <div className="boxx">
      <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        <Grid item xs={6} md={8}>
          <Item>
            <Path_tables />
          </Item>
        </Grid>
        <Grid item xs={6} md={4}>
          <Item>
            <h2>SHORTEST PATH USING REINFORCEMENT LEARNING</h2>
            <p>
            Reinforcement learning is a type of machine learning in which an agent learns to make decisions by interacting with an environment. The agent receives feedback in the form of rewards or penalties based on its actions, and the goal of the agent is to maximize the cumulative reward it receives over time.

            Monte Carlo algorithm is a reinforcement learning method that uses experience to learn from the past. In the context of routing in a Ryu controller, Monte Carlo algorithm can be used to optimize the routing decisions made by the controller.

            The basic idea of Monte Carlo algorithm is to use samples of actual experience to estimate the value of a state or action. In routing, the states can be the network topology and the actions can be the paths taken by the packets. The algorithm starts with a random policy and iteratively improves the policy based on the reward signals obtained from the environment.

            In the context of routing in a Ryu controller, the Monte Carlo algorithm can be used to optimize the routing decisions made by the controller. The algorithm can be applied in two phases: an off-policy phase and an on-policy phase. In the off-policy phase, the algorithm generates a set of trajectories by following a random policy. In the on-policy phase, the algorithm uses the trajectories to estimate the value of each state and action, and updates the policy accordingly.

            The Monte Carlo algorithm can be a powerful tool for optimizing routing decisions in a Ryu controller. By using actual experience to estimate the value of states and actions, the algorithm can learn to make optimal routing decisions in complex and dynamic network environments. 
            </p>
          </Item>
        </Grid>
      </Grid>
    </Box>
      </div>


    </div>
  );
}

export default Output;
