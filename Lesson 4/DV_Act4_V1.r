#%load_ext rpy2.ipython

#import rpy2.situation

# Installing R packages and setting up personal library path, idk if this is needed but we can delete cell if not
%%R
# Set personal library path (change if you prefer another folder)
personal_lib <- file.path(Sys.getenv("USERPROFILE"), "R", "win-library", "4.5")

# Create the folder if it doesn't exist
if (!dir.exists(personal_lib)) {
  dir.create(personal_lib, recursive = TRUE)
  message("Created personal library at: ", personal_lib)
}

# Add it to R's library search path
.libPaths(c(personal_lib, .libPaths()))

install.packages("dplyr", 
                 repos = "https://cloud.r-project.org", 
                 lib = personal_lib)

library(dplyr)

install.packages("ggplot2", 
                 repos = "https://cloud.r-project.org", 
                 lib = personal_lib)

# Made boxplot in R, just to say we did something ig
%%R -i df
library(ggplot2)
ggplot(df, aes(x = Region, y = Sales, fill = Category)) +
  geom_boxplot() +
  theme_minimal()