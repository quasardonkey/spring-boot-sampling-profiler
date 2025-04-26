# Spring Boot Sampling Profiler
This is a sampling profiler for Spring Boot applications using `/actuator/threaddump` endpoint. It periodically collects
thread dumps from your application and analyzes them to provide insights into method execution times and depths.
This can be used to identify code hotspots.

## How It Works
- The profiler periodically requests thread dumps from the specified URL, according to the configured intervals.
- It filters the stack traces based on the provided package or method filter.
- It counts the occurrences of methods and records their average execution depths.
- It writes results to a CSV file.

## Prerequisites
Ensure that the `threaddump` endpoint is exposed by Spring Boot Actuator in your application.yml:
```yaml
management:
    endpoints:
        web:
            exposure:
                include: info, health, loggers, metrics, threaddump
```

## Configuration settings
The config.json file contains the following settings:

| Setting        | Description                                | Example                                   |
|----------------|--------------------------------------------|-------------------------------------------|
| url            | URL to scrape                              | http://localhost:8080/actuator/threaddump |
| samples        | Number of samples to take                  | 100                                       |
| min_interval   | Minimum sleep time between samples         | 1.0                                       |
| max_interval   | Maximum sleep time between samples         | 5.0                                       |
| package_filter | Only report samples with this package      | com.example.project                       |
| method_filter  | Only report this method or its descendants | com.example.project.MyService#myMethod    |
| output_file    | Path to output CSV file                    | report.csv                                |

## Running the profiler
By default, the profiler will read options from `config.json`, and write output to `sampler_report.csv`:
```shell
./profiler.py
```

Command usage:
```text
usage: profiler.py [-h] [--config CONFIG] [--output OUTPUT]

Profile a Java application using Spring Actuator thread dump endpoint.

options:
  -h, --help       show this help message and exit
  --config CONFIG  Path to the config file
  --output OUTPUT  Path to the output CSV file
```

## Example Output

Here is an excerpt from an output CSV:

| Method                                                      | Count | Average Depth |
|-------------------------------------------------------------|-------|---------------|
| java.lang.Thread.run                                        | 16    | 0             |
| com.example.project.Bookstore.createBook                    | 7     | 47            |
| org.postgresql.core.PGStream.receive                        | 1     | 180           |
| sun.nio.ch.NioSocketImpl.tryRead                            | 2     | 194           |
