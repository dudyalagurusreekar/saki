import { apiClient } from "./apiClient";

export const getTest = async () => {
  const res = await apiClient.get("/");
  return res.data;
};