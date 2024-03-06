-- Optional: Create a new database if you don't already have one
CREATE DATABASE IF NOT EXISTS aws_costs_db;
USE aws_costs_db;

-- Create the aws_costs table
CREATE TABLE IF NOT EXISTS aws_costs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(255),
    ec2_cost INT,
    lambda_cost INT,
    total_cost INT
);

-- Insert data into the aws_costs table
INSERT INTO aws_costs (user_name, ec2_cost, lambda_cost, total_cost) 
VALUES 
    ('Bhavya', 100, 50, 150),
    ('Pradhumna', 150, 60, 210),
    ('Susanta', 120, 40, 160);
