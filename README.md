# Mini Logistics Manager v2

A desktop-based logistics management application built with **Python, Tkinter, and SQLite**. It helps manage shipments, drivers, delivery statuses, and logistics reports through a simple graphical user interface.

## Features

- **Dashboard:** View total shipments, revenue, and shipment statistics.
- **Shipment Management:** Create, search, update, and delete shipments.
- **Shipment Tracking:** Generate unique tracking codes for every shipment.
- **Driver Management:** Add, view, and delete drivers.
- **Driver Assignment:** Assign drivers to specific shipments.
- **Status Management:** Track shipments through Pending, In Transit, and Delivered.
- **CSV Export:** Export shipment records into CSV files.
- **SQLite Database:** Store application data locally.
- **Desktop Application:** Run the application as a standalone Windows executable.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Tkinter | Graphical user interface |
| SQLite | Database management |
| CSV | Data export |
| UUID | Unique tracking code generation |
| PyInstaller | Windows executable packaging |

## Project Structure

```text
Mini-Logistics-Manager/
│
├── mini_logistics_gui.py
├── main.py
├── logistics.db
├── shipments_export.csv
│
├── build/
├── dist/
│   └── mini_logistics_gui.exe
│
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/USERNAME/mini-logistics-manager.git
```

### 2. Navigate to the project folder

```bash
cd mini-logistics-manager
```

### 3. Run the application

```bash
python mini_logistics_gui.py
```

### 4. Build the Windows executable

Install PyInstaller:

```bash
python -m pip install pyinstaller
```

Build the application:

```bash
python -m PyInstaller --onefile --windowed mini_logistics_gui.py
```

The executable will be generated inside the `dist/` directory.

## Database

The application uses SQLite to store:

- Shipments
- Drivers
- Shipment statuses
- Driver assignments
- Delivery information

The database is created automatically when the application starts.

## Shipment Pricing

The application calculates shipping prices using the following formula:

```python
BASE_FEE = 25.0
PRICE_PER_KG = 8.0

price = BASE_FEE + (PRICE_PER_KG * weight_kg)
```

## Future Improvements

- User authentication and admin roles.
- Modern interface with dark mode.
- PDF invoice and shipping label generation.
- Delivery history and activity logs.
- Database backup and restore.
- Advanced reporting and analytics.

## Author

**Mohammed Maghraoui**

Full Stack Web Developer | Python Developer

- GitHub: [MohammedMaghraoui](https://github.com/MohammedMaghraoui)
- LinkedIn: [Mohammed Maghraoui](https://www.linkedin.com/in/mohammed-maghraoui/)

## License

This project is available for educational and portfolio purposes.
