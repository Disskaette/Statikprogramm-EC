/**
 * TypeScript interfaces for project and position API response shapes.
 *
 * These mirror the Pydantic models in web/api/routes/projects.py.
 */

// ---------------------------------------------------------------------------
// Project
// ---------------------------------------------------------------------------

export interface Project {
  /** UUID v4 string – unique project identifier */
  uuid: string;
  /** Human-readable project name */
  name: string;
  /** ISO 8601 creation timestamp */
  created: string;
  /** ISO 8601 last-modified timestamp */
  last_modified: string;
  /** Optional project description */
  description: string;
  /** Relative paths of all positions in this project */
  positions: string[];
  /** Absolute filesystem path of the project directory */
  path: string;
}

// ---------------------------------------------------------------------------
// Position
// ---------------------------------------------------------------------------

export interface Position {
  /** Position number string, e.g. "1.01" */
  position_nummer: string;
  /** Human-readable position name, e.g. "HT 1 – Wohnzimmer" */
  position_name: string;
  /** ISO 8601 creation timestamp */
  created: string;
  /** ISO 8601 last-modified timestamp */
  last_modified: string;
  /** Active module key, e.g. "durchlauftraeger" */
  active_module: string;
  /**
   * Module data keyed by module name.
   * The "durchlauftraeger" entry stores the CalculationRequest shape.
   */
  modules: Record<string, unknown>;
  /** Absolute filesystem path of the position JSON file */
  file_path: string;
  /** Path of the position relative to the project root, e.g. "EG/Position_1_01.json" */
  relative_path: string;
}
