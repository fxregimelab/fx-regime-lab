-- v2.0: Add FPI flow column for USDINR signal augmentation
ALTER TABLE signals ADD COLUMN fpi_flow DOUBLE PRECISION;
