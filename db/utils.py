import sqlite3
import json


def initialise_ir_data_tables(conn):
    """
    Initializes the IR data tables in the database.

    Args:
        conn (sqlite3.Connection): The SQLite database connection object.

    Returns:
        None

    Raises:
        sqlite3.Error: If there is an error creating the tables.

    """
    try:
        with conn:
            cur = conn.cursor()
            # Create main_object_table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS main_object_table (
                    main_object_id INTEGER PRIMARY KEY,
                    name TEXT,
                    protocol INTEGER,
                    address INTEGER,
                    command INTEGER,
                    rawdata_length INTEGER
                )
            ''')

            # Create raw_data_table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS raw_data_table (
                    raw_data_id INTEGER PRIMARY KEY,
                    main_object_id INTEGER,
                    data_order INTEGER,
                    data_value INTEGER,
                    FOREIGN KEY (main_object_id) REFERENCES main_object_table(main_object_id)
                )
            ''')
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
    else:
        print("Tables created successfully.")


def insert_ir_data(conn, data, name) -> bool:
    """
    Inserts IR data into the database.

    Args:
        conn (sqlite3.Connection): The database connection.
        data (dict): The IR data to be inserted.
        name (str): The name of the IR data.

    Returns:
        None
    """
    try:
        with conn:
            cur = conn.cursor()
            # Insert data into main_object_table
            cur.execute(
                'INSERT INTO main_object_table (name, protocol, address, command, rawdata_length) VALUES (?, ?, ?, ?, ?)',
                (name, data['PROTOCOL'], data['ADDRESS'],
                 data['COMMAND'], data['RAWDATALENGTH'])
            )
            main_object_id = cur.lastrowid

            # Insert data into raw_data_table
            raw_data_values = [(main_object_id, index, value)
                               for index, value in enumerate(data['RAWDATA'])]
            cur.executemany(
                'INSERT INTO raw_data_table (main_object_id, data_order, data_value) VALUES (?, ?, ?)',
                raw_data_values
            )
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
        return False
    else:
        print("Data inserted successfully.")
        return True


def retrieve_ir_data_by_name(conn, name):
    """
    Retrieve infrared (IR) data by name from the database.

    Args:
        conn (sqlite3.Connection): The SQLite database connection.
        name (str): The name of the IR data to retrieve.

    Returns:
        tuple or None: A tuple containing the retrieved IR data, or None if no data is found.

    Raises:
        sqlite3.Error: If there is an error retrieving the data from the database.
    """
    try:
        with conn:
            cur = conn.cursor()
            # Query to retrieve main object data along with associated raw data
            cur.execute('''
                SELECT
                    m.protocol, m.address, m.command, m.rawdata_length, group_concat(r.data_value, ',') AS rawdata
                FROM
                    main_object_table m
                JOIN
                    raw_data_table r ON m.main_object_id = r.main_object_id
                WHERE
                    m.name = ?
                GROUP BY
                    m.main_object_id
            ''', (name,))

            row = cur.fetchone()
            if row:
                return row
            else:
                return None
    except sqlite3.Error as e:
        print(f"Error retrieving data: {e}")
        return None


def reconstruct_json_string_from_db_row(row) -> str:
    """
    Reconstructs a JSON string from a database row.

    Args:
        row: A database row containing the necessary data.

    Returns:
        A JSON string representing the reconstructed data.

    Raises:
        None.
    """
    if row:
        main_object = {
            "PROTOCOL": row[0],
            "ADDRESS": row[1],
            "COMMAND": row[2],
            "RAWDATA": list(map(int, row[4].split(','))),
            "RAWDATALENGTH": row[3]
        }
        print("Retrieved main object data successfully!")
        return json.dumps(main_object, indent=None, separators=(',', ':'))
    else:
        return None


def retrieve_all_ir_names(conn) -> list[str]:
    """
    Retrieve all IR data names from the database.

    Args:
        conn (sqlite3.Connection): The SQLite database connection.

    Returns:
        list: A list of IR data names.

    Raises:
        sqlite3.Error: If there is an error retrieving the data from the database.
    """
    try:
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT name FROM main_object_table')
            rows = cur.fetchall()
            return [row[0] for row in rows]
    except sqlite3.Error as e:
        print(f"Error retrieving data: {e}")
        return []


def main():
    try:
        # Connect to SQLite database (creates if not exists)
        conn = sqlite3.connect('stored-options.db')
        initialise_ir_data_tables(conn)

        # Sample JSON string
        json_string = '{"PROTOCOL":11,"ADDRESS":8,"COMMAND":50,"RAWDATA":[70,33,10,7,10,25,10,7,10,7,10,7,10,7,11,6,11,7,9,8,10,7,10,8,10,6,11,6,11,24,11,7,9,8,10,7,10,7,10,8,10,7,10,7,10,7,10,7,10,25,10,6,11,7,10,8,10,7,10,7,11,6,11,6,10,8,10,7,10,24,11,7,10,7,10,24,11,23,11,7,10,7,10,7,11,23,11,7,10,7,11,23,10,24,11,7,10,24,11],"RAWDATALENGTH":99}'
        print(json_string)
        # Parse JSON string
        data = json.loads(json_string)

        name = "test2"
        # Insert data into tables
        insert_ir_data(conn, data, name)

        # Retrieve data and reconstruct JSON
        retrieve_ir_data_by_name(conn, name)

    except Exception as e:
        print("Error:", e)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
