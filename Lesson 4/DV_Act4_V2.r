# Install if needed:
# install.packages(c("tidyverse", "lubridate"))

library(tidyverse)
library(lubridate)

url <- "https://raw.githubusercontent.com/MaharLeika18/Datasets/refs/heads/main/Sample_Superstore.csv"

df <- read.csv(url, row.names = 1, stringsAsFactors = FALSE)

# Data Cleaning
# ------------------------------------------------------------------------------
# Show duplicate rows
duplicates <- df[duplicated(df) | duplicated(df, fromLast = TRUE), ]
duplicates
nrow(duplicates)

# Remove duplicates
df <- df[!duplicated(df), ]

# Drop irrelevant columns
df <- df |> select(-Country)

# Normalize delimiters
df$`Order Date` <- gsub("-", "/", df$`Order Date`)
df$`Ship Date`  <- gsub("-", "/", df$`Ship Date`)

# Convert to Date
df$`Order Date` <- as.Date(df$`Order Date`, format = "%m/%d/%Y")
df$`Ship Date`  <- as.Date(df$`Ship Date`, format = "%m/%d/%Y")

# Assign data types
df$Sales  <- as.numeric(df$Sales)
df$Profit <- as.numeric(df$Profit)

df$Region       <- as.factor(df$Region)
df$Category     <- as.factor(df$Category)
df$`Sub-Category` <- as.factor(df$`Sub-Category`)

# Handle missing values
# ------------------------------------------------------------------------------
# Inspect rows with NA
df[!complete.cases(df), ]

# Count NA per column
colSums(is.na(df))

# Feature Engineering
# ------------------------------------------------------------------------------
# Order Month (Year-Month format)
df$`Order Date (Month)` <- format(df$`Order Date`, "%Y-%m")

# Profit Margin
df$`Profit Margin` <- (df$Profit / df$Sales) * 100

# Year Quarter
df$YearQuarter <- paste0(year(df$`Order Date`), "Q", quarter(df$`Order Date`))

# Feature Aggregation
# ------------------------------------------------------------------------------
sales_by_region <- df |>
  group_by(Region) |>
  summarise(Sales = sum(Sales, na.rm = TRUE)) |>
  ungroup()

monthly_revenue <- df |>
  group_by(`Order Date (Month)`) |>
  summarise(Sales = sum(Sales, na.rm = TRUE)) |>
  arrange(`Order Date (Month)`)

quarterly_revenue <- df |>
  group_by(YearQuarter) |>
  summarise(Sales = sum(Sales, na.rm = TRUE)) |>
  arrange(YearQuarter)

quarterly_revenue$QuarterLabel <- gsub("Q", " - Q", quarterly_revenue$YearQuarter)

avg_profit_by_product <- df |>
  group_by(`Product Name`) |>
  summarise(AvgProfit = mean(Profit, na.rm = TRUE)) |>
  ungroup()

# Inspect dataframes
head(df, 5)
sales_by_region
monthly_revenue
avg_profit_by_product

# Data Visualization
# ------------------------------------------------------------------------------
ggplot(sales_by_region, aes(x = Sales, y = Region)) +
  geom_bar(stat = "identity") +
  labs(title = "Sales by Region",
       x = "Sales",
       y = "Region") +
  theme_minimal()

ggplot(quarterly_revenue, aes(x = QuarterLabel, y = Sales, group = 1)) +
  geom_line() +
  geom_point() +
  labs(title = "Quarterly Sales",
       x = "Quarter",
       y = "Sales") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))