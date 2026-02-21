require('dotenv').config({ path: '../.env' });
const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
const port = 3001;

// ─── Configuration PostgreSQL ─────────────────────────────────────────────────
const pool = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
});

app.use(cors());
app.use(express.json());

// ─── Route de santé ───────────────────────────────────────────────────────────
app.get('/api/health', async (req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  } catch (err) {
    res.status(500).json({ status: 'error', message: err.message });
  }
});

// ─── Route : Données RÉELLES uniquement ──────────────────────────────────────
app.get('/api/data/real', async (req, res) => {
  try {
    const { range, start, end } = req.query;

    let query;
    let params = [];

    // Option 1 : Utiliser start & end (format ISO)
    if (start && end) {
      query = `
        SELECT 
          (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date, 
          value AS "true value",
          'RTE' AS source
        FROM historical_data
        WHERE timestamp >= $1 AND timestamp <= $2
        ORDER BY timestamp ASC
      `;
      params = [start, end];
    }
    // Option 2 : Utiliser range (7d, 30d, 90d)
    else {
      let daysToSubtract = 90;
      if (range === '7d') daysToSubtract = 7;
      else if (range === '30d') daysToSubtract = 30;

      query = `
        SELECT 
          (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
          value AS "true value",
          'RTE' AS source
        FROM historical_data
        WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
        ORDER BY timestamp ASC
      `;
    }

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (err) {
    console.error('Erreur /api/data/real:', err);
    res.status(500).json({ error: 'Erreur serveur', message: err.message });
  }
});

// ─── Route : PRÉDICTIONS uniquement ───────────────────────────────────────────
app.get('/api/data/predictions', async (req, res) => {
  try {
    const { range, start, end } = req.query;

    let query;
    let params = [];

    // Option 1 : Utiliser start & end
    if (start && end) {
      query = `
        SELECT 
          (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
          predicted_value AS "our forecast",
          model_name AS model
        FROM predictions
        WHERE timestamp >= $1 AND timestamp <= $2
        ORDER BY timestamp ASC
      `;
      params = [start, end];
    }
    // Option 2 : Utiliser range (7d, 30d, 90d)
    else {
      let daysToSubtract = 90;
      if (range === '7d') daysToSubtract = 7;
      else if (range === '30d') daysToSubtract = 30;

      query = `
        SELECT 
          (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
          predicted_value AS "our forecast",
          model_name AS model
        FROM predictions
        WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
        ORDER BY timestamp ASC
      `;
    }

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (err) {
    console.error('Erreur /api/data/predictions:', err);
    res.status(500).json({ error: 'Erreur serveur', message: err.message });
  }
});

// ─── Route : Prévisions RTE uniquement ────────────────────────────────────────
app.get('/api/data/rte-forecasts', async (req, res) => {
  try {
    const { range, start, end } = req.query;

    let query;
    let params = [];

    // Option 1 : Utiliser start & end
    if (start && end) {
      query = `
        SELECT 
          (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
          forecast_value AS "rte forecast",
          'RTE' AS source
        FROM rte_forecasts
        WHERE timestamp >= $1 AND timestamp <= $2
        ORDER BY timestamp ASC
      `;
      params = [start, end];
    }
    // Option 2 : Utiliser range (7d, 30d, 90d)
    else {
      let daysToSubtract = 90;
      if (range === '7d') daysToSubtract = 7;
      else if (range === '30d') daysToSubtract = 30;

      query = `
        SELECT 
          (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
          forecast_value AS "rte forecast",
          'RTE' AS source
        FROM rte_forecasts
        WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
        ORDER BY timestamp ASC
      `;
    }

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (err) {
    console.error('Erreur /api/data/rte-forecasts:', err);
    res.status(500).json({ error: 'Erreur serveur', message: err.message });
  }
});

// ─── Route : Données combinées (OPTIONNEL - pour compatibilité) ──────────────
app.get('/api/data', async (req, res) => {
  try {
    const { range } = req.query;

    let daysToSubtract = 90;
    if (range === '7d') daysToSubtract = 7;
    else if (range === '30d') daysToSubtract = 30;

    // Données réelles
    const realResult = await pool.query(`
      SELECT 
        (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
        value AS "true value"
      FROM historical_data
      WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
      ORDER BY timestamp ASC
    `);

    // Prédictions Chronos
    const predResult = await pool.query(`
      SELECT 
        (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
        predicted_value AS "our forecast"
      FROM predictions
      WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
      ORDER BY timestamp ASC
    `);

    // Prévisions RTE
    const rteResult = await pool.query(`
      SELECT 
        (timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Paris') AS date,
        forecast_value AS "rte forecast"
      FROM rte_forecasts
      WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
      ORDER BY timestamp ASC
    `);

    // Fusion des 3 sources par timestamp
    const realMap = new Map();
    realResult.rows.forEach(row => {
      realMap.set(new Date(row.date).toISOString(), row["true value"]);
    });

    const predMap = new Map();
    predResult.rows.forEach(row => {
      predMap.set(new Date(row.date).toISOString(), row["our forecast"]);
    });

    const rteMap = new Map();
    rteResult.rows.forEach(row => {
      rteMap.set(new Date(row.date).toISOString(), row["rte forecast"]);
    });

    // Union de tous les timestamps
    const allDates = new Set([...realMap.keys(), ...predMap.keys(), ...rteMap.keys()]);
    const combined = Array.from(allDates)
      .sort((a, b) => new Date(a) - new Date(b))  // Tri croissant
      .map(date => ({
        date,
        "true value": realMap.get(date) ?? null,
        "rte forecast": rteMap.get(date) ?? null,
        "our forecast": predMap.get(date) ?? null,
        
      }));

    res.json(combined);
  } catch (err) {
    console.error('Erreur /api/data:', err);
    res.status(500).json({ error: 'Erreur serveur', message: err.message });
  }
});

// ─── Route : statut système ───────────────────────────────────────────────────
app.get('/api/status', async (req, res) => {
  try {
    const realCount = await pool.query('SELECT COUNT(*) FROM historical_data');
    const predCount = await pool.query('SELECT COUNT(*) FROM predictions');
    const rteCount = await pool.query('SELECT COUNT(*) FROM rte_forecasts');
    const lastReal = await pool.query('SELECT MAX(timestamp) FROM historical_data');
    const lastPred = await pool.query('SELECT MAX(prediction_date) FROM predictions');
    const lastRTE = await pool.query('SELECT MAX(timestamp) FROM rte_forecasts');

    res.json({
      historical_data: {
        count: parseInt(realCount.rows[0].count),
        last_timestamp: lastReal.rows[0].max,
      },
      predictions: {
        count: parseInt(predCount.rows[0].count),
        last_generated: lastPred.rows[0].max,
      },
      rte_forecasts: {
        count: parseInt(rteCount.rows[0].count),
        last_timestamp: lastRTE.rows[0].max,
      }
    });
  } catch (err) {
    console.error('Erreur /api/status:', err);
    res.status(500).json({ error: 'Erreur serveur' });
  }
});

app.listen(port, () => {
  console.log(`API Express lancée sur http://localhost:${port}`);
});

















// require('dotenv').config({ path: '../.env' });
// const express = require('express');
// const cors = require('cors');
// const { Pool } = require('pg');

// const app = express();
// const port = 3001;

// // ─── Configuration PostgreSQL ─────────────────────────────────────────────────
// const pool = new Pool({
//   host: process.env.DB_HOST,
//   port: process.env.DB_PORT,
//   database: process.env.DB_NAME,
//   user: process.env.DB_USER,
//   password: process.env.DB_PASSWORD,
// });



// app.use(cors());
// app.use(express.json());

// // ─── Route de santé ───────────────────────────────────────────────────────────
// app.get('/api/health', async (req, res) => {
//   try {
//     await pool.query('SELECT 1');
//     res.json({ status: 'ok', timestamp: new Date().toISOString() });
//   } catch (err) {
//     res.status(500).json({ status: 'error', message: err.message });
//   }
// });

// // ─── Route principale : données réelles + prédictions combinées ───────────────
// app.get('/api/data', async (req, res) => {
//   try {
//     const { range } = req.query;

//     let daysToSubtract = 90;
//     if (range === '7d') daysToSubtract = 7;
//     else if (range === '30d') daysToSubtract = 30;

//     // Données réelles
//     const realResult = await pool.query(`
//     SELECT timestamp AS date, value AS "true value"
//     FROM historical_data
//     WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
//     ORDER BY timestamp ASC
//     `);

//     // Prédictions Chronos
//     const predResult = await pool.query(`
//     SELECT timestamp AS date, predicted_value AS "our forecast"
//     FROM predictions
//     WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
//     ORDER BY timestamp ASC
//     `);

//     // Prévisions RTE
//     const rteResult = await pool.query(`
//     SELECT timestamp AS date, forecast_value AS "rte forecast"
//     FROM rte_forecasts
//     WHERE timestamp >= NOW() - INTERVAL '${daysToSubtract} days'
//     ORDER BY timestamp ASC
//     `);

//     // Fusion des 3 sources par timestamp
//     const realMap = new Map();
//     realResult.rows.forEach(row => {
//     realMap.set(new Date(row.date).toISOString(), row["true value"]);
//     });

//     const predMap = new Map();
//     predResult.rows.forEach(row => {
//     predMap.set(new Date(row.date).toISOString(), row["our forecast"]);
//     });

//     const rteMap = new Map();
//     rteResult.rows.forEach(row => {
//     rteMap.set(new Date(row.date).toISOString(), row["rte forecast"]);
//     });

//     // Union de tous les timestamps
//     const allDates = new Set([...realMap.keys(), ...predMap.keys(), ...rteMap.keys()]);
//     const combined = Array.from(allDates)
//     .sort()
//     .map(date => ({
//         date,
//         "true value": realMap.get(date) ?? null,
//         "our forecast": predMap.get(date) ?? null,
//         "rte forecast": rteMap.get(date) ?? null,
//     }));

//     res.json(combined);
//   } catch (err) {
//     console.error('Erreur /api/data:', err);
//     res.status(500).json({ error: 'Erreur serveur', message: err.message });
//   }
// });

// // ─── Route : statut système ───────────────────────────────────────────────────
// app.get('/api/status', async (req, res) => {
//   try {
//     const realCount = await pool.query('SELECT COUNT(*) FROM historical_data');
//     const predCount = await pool.query('SELECT COUNT(*) FROM predictions');
//     const lastReal  = await pool.query('SELECT MAX(timestamp) FROM historical_data');
//     const lastPred  = await pool.query('SELECT MAX(prediction_date) FROM predictions');

//     res.json({
//       historical_data: {
//         count: parseInt(realCount.rows[0].count),
//         last_timestamp: lastReal.rows[0].max,
//       },
//       predictions: {
//         count: parseInt(predCount.rows[0].count),
//         last_generated: lastPred.rows[0].max,
//       }
//     });
//   } catch (err) {
//     console.error('Erreur /api/status:', err);
//     res.status(500).json({ error: 'Erreur serveur' });
//   }
// });

// app.listen(port, () => {
//   console.log(`API Express lancée sur http://localhost:${port}`);
// });