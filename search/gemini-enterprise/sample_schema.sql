-- HR Database Schema

-- Table: Departments
-- Stores information about different departments within the organization.
CREATE TABLE Departments (
    department_id INT PRIMARY KEY AUTO_INCREMENT, -- Unique identifier for the department (AUTO_INCREMENT for MySQL/SQL Server, SERIAL for PostgreSQL)
    department_name VARCHAR(100) NOT NULL UNIQUE, -- Name of the department, must be unique
    location VARCHAR(255),                       -- Physical location of the department
    phone_number VARCHAR(20),                    -- Contact number for the department
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the record was created
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP -- Timestamp for last update (for MySQL, similar triggers needed for others)
);

-- Table: JobTitles
-- Stores information about different job titles/roles.
CREATE TABLE JobTitles (
    job_id INT PRIMARY KEY AUTO_INCREMENT,       -- Unique identifier for the job title
    job_title VARCHAR(100) NOT NULL UNIQUE,      -- Name of the job title, must be unique
    min_salary DECIMAL(10, 2),                   -- Minimum salary for this job title
    max_salary DECIMAL(10, 2),                   -- Maximum salary for this job title
    job_description TEXT,                        -- Detailed description of the job
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table: Employees
-- Core table storing employee personal and professional information.
CREATE TABLE Employees (
    employee_id INT PRIMARY KEY AUTO_INCREMENT,   -- Unique identifier for the employee
    first_name VARCHAR(50) NOT NULL,              -- Employee's first name
    last_name VARCHAR(50) NOT NULL,               -- Employee's last name
    email VARCHAR(100) NOT NULL UNIQUE,           -- Employee's email address, must be unique
    phone_number VARCHAR(20),                     -- Employee's phone number
    hire_date DATE NOT NULL,                      -- Date when the employee was hired
    job_id INT NOT NULL,                          -- Foreign Key to JobTitles
    department_id INT NOT NULL,                   -- Foreign Key to Departments
    manager_id INT,                               -- Foreign Key to Employees (self-referencing for managers)
    salary DECIMAL(10, 2) NOT NULL,               -- Employee's current salary
    date_of_birth DATE,                           -- Employee's date of birth
    gender ENUM('Male', 'Female', 'Other', 'Prefer not to say'), -- Employee's gender (ENUM is MySQL specific, use CHECK constraint for others)
    address VARCHAR(255),                         -- Employee's home address
    city VARCHAR(100),                            -- Employee's city
    state VARCHAR(100),                           -- Employee's state/province
    zip_code VARCHAR(20),                         -- Employee's zip/postal code
    country VARCHAR(100),                         -- Employee's country
    is_active BOOLEAN DEFAULT TRUE,               -- Is the employee currently active?
    termination_date DATE,                        -- Date of termination if applicable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES JobTitles(job_id),
    FOREIGN KEY (department_id) REFERENCES Departments(department_id),
    FOREIGN KEY (manager_id) REFERENCES Employees(employee_id)
);

-- Table: Dependents
-- Stores information about employee's dependents (for benefits, emergency contacts, etc.).
CREATE TABLE Dependents (
    dependent_id INT PRIMARY KEY AUTO_INCREMENT,  -- Unique identifier for the dependent
    employee_id INT NOT NULL,                     -- Foreign Key to Employees
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    relationship VARCHAR(50),                     -- e.g., 'Spouse', 'Child', 'Parent'
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE CASCADE -- If employee deleted, dependents also deleted
);

-- Table: Benefits
-- Defines different types of benefits offered by the company.
CREATE TABLE Benefits (
    benefit_id INT PRIMARY KEY AUTO_INCREMENT,    -- Unique identifier for the benefit
    benefit_name VARCHAR(100) NOT NULL UNIQUE,    -- Name of the benefit (e.g., 'Health Insurance', 'Dental', '401k')
    description TEXT,                             -- Description of the benefit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table: EmployeeBenefits
-- Links employees to the benefits they are enrolled in.
CREATE TABLE EmployeeBenefits (
    employee_id INT NOT NULL,
    benefit_id INT NOT NULL,
    enrollment_date DATE,                         -- Date when the employee enrolled
    coverage_start_date DATE,                     -- Date when coverage begins
    coverage_end_date DATE,                       -- Date when coverage ends
    PRIMARY KEY (employee_id, benefit_id),        -- Composite primary key
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (benefit_id) REFERENCES Benefits(benefit_id)
);

-- Table: PerformanceReviews
-- Stores information about employee performance reviews.
CREATE TABLE PerformanceReviews (
    review_id INT PRIMARY KEY AUTO_INCREMENT,     -- Unique identifier for the review
    employee_id INT NOT NULL,                     -- Foreign Key to Employees (employee being reviewed)
    reviewer_id INT NOT NULL,                     -- Foreign Key to Employees (employee conducting the review)
    review_date DATE NOT NULL,                    -- Date of the review
    rating DECIMAL(3, 1),                         -- Numerical rating (e.g., 1.0-5.0)
    comments TEXT,                                -- General comments
    goals_achieved TEXT,                          -- Text describing goals achieved
    development_areas TEXT,                       -- Text describing areas for development
    next_review_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id),
    FOREIGN KEY (reviewer_id) REFERENCES Employees(employee_id)
);

-- Table: TrainingPrograms
-- Defines available training programs.
CREATE TABLE TrainingPrograms (
    program_id INT PRIMARY KEY AUTO_INCREMENT,    -- Unique identifier for the training program
    program_name VARCHAR(150) NOT NULL UNIQUE,    -- Name of the program
    description TEXT,
    duration_hours INT,                           -- Duration in hours
    cost DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table: EmployeeTraining
-- Records employee's participation in training programs.
CREATE TABLE EmployeeTraining (
    employee_id INT NOT NULL,
    program_id INT NOT NULL,
    completion_date DATE,                         -- Date training was completed
    grade VARCHAR(10),                            -- Grade or status (e.g., 'Pass', 'Fail', 'In Progress')
    PRIMARY KEY (employee_id, program_id),        -- Composite primary key
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (program_id) REFERENCES TrainingPrograms(program_id)
);

-- Table: Absences
-- Tracks employee absences (sick leave, vacation, etc.).
CREATE TABLE Absences (
    absence_id INT PRIMARY KEY AUTO_INCREMENT,    -- Unique identifier for the absence record
    employee_id INT NOT NULL,                     -- Foreign Key to Employees
    absence_type VARCHAR(50) NOT NULL,            -- e.g., 'Sick Leave', 'Vacation', 'Unpaid Leave'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    approved_by INT,                              -- Foreign Key to Employees (approving manager)
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending', -- (ENUM is MySQL specific, use CHECK constraint for others)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id),
    FOREIGN KEY (approved_by) REFERENCES Employees(employee_id)
);

-- Table: EmergencyContacts
-- Stores emergency contact information for employees.
CREATE TABLE EmergencyContacts (
    contact_id INT PRIMARY KEY AUTO_INCREMENT,    -- Unique identifier for the contact
    employee_id INT NOT NULL,                     -- Foreign Key to Employees
    name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50),
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE CASCADE
);

-- Table: Credentials
-- Stores information about employee's professional licenses, certifications etc.
CREATE TABLE Credentials (
    credential_id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id INT NOT NULL,
    credential_name VARCHAR(100) NOT NULL,
    issuing_organization VARCHAR(100),
    issue_date DATE,
    expiration_date DATE,
    credential_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE CASCADE
);

-- Table: Skills
-- Defines various skills that employees might possess.
CREATE TABLE Skills (
    skill_id INT PRIMARY KEY AUTO_INCREMENT,
    skill_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table: EmployeeSkills
-- Associates employees with their skills and proficiency levels.
CREATE TABLE EmployeeSkills (
    employee_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level ENUM('Beginner', 'Intermediate', 'Advanced', 'Expert'), -- (ENUM is MySQL specific, use CHECK constraint for others)
    years_experience DECIMAL(4, 1),
    PRIMARY KEY (employee_id, skill_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES Skills(skill_id)
);


-- DDL for PostgreSQL Specifics (if using PostgreSQL, replace AUTO_INCREMENT with SERIAL, and ENUM with CHECK)
/*
-- Example for PostgreSQL:
CREATE TABLE Departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    location VARCHAR(255),
    phone_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- For gender/status ENUMs in PostgreSQL, use CHECK constraints:
gender VARCHAR(20),
CONSTRAINT check_gender CHECK (gender IN ('Male', 'Female', 'Other', 'Prefer not to say')),

status VARCHAR(20) DEFAULT 'Pending',
CONSTRAINT check_status CHECK (status IN ('Pending', 'Approved', 'Rejected')),

proficiency_level VARCHAR(20),
CONSTRAINT check_proficiency_level CHECK (proficiency_level IN ('Beginner', 'Intermediate', 'Advanced', 'Expert')),

-- To automatically update 'updated_at' in PostgreSQL, you typically use a trigger:
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_departments_timestamp
BEFORE UPDATE ON Departments
FOR EACH ROW EXECUTE FUNCTION update_timestamp();
-- (Repeat for other tables)
*/
