import axios from 'axios';
import { baseURL } from './URL';

const API = axios.create({
  baseURL: baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const postText = async (text) => {
  try {
    const { data } = await API.post('/dummies/', { text } );
    return data;
  } catch (error) {
    console.log(error);
  }
};

