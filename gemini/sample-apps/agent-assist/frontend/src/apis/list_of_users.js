import axios from "axios";
const BACKENDURL = process.env.REACT_APP_API_URL;
const BASE_URL = BACKENDURL + "/users";

console.log(BASE_URL);

export default axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-type": "application/json",
    Accept: "application/json",
  },
});
