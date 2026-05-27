variable "aws_region" {
  description = "AWS Region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "hackathon"
}


variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "budgetbot"
}

variable "project" {
  description = "Project tag required by W7"
  type        = string
  default     = "W7Capstone"
}

variable "team" {
  description = "Team tag required by W7"
  type        = string
  default     = "G13"
}

variable "owner" {
  description = "Owner email for cost allocation"
  type        = string
  default     = "ptientr.dev@gmail.com"
}

variable "cost_center" {
  description = "Cost center ID for cost allocation"
  type        = string
  default     = "G13"
}
