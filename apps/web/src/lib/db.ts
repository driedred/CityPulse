import { Client } from "pg";

const client = new Client({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT || 5432),
  database: process.env.DB_NAME,
  user: process.env.DB_USERNAME,
  password: process.env.DB_PASSWORD,
});

client.connect()
  .then(() => console.log("Connected to Supabase"))
  .catch((err) => console.error("DB connection error:", err));

export default client;
