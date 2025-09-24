resource "aws_vpc" "vpc171" {
  cidr_block = "10.107.0.0/16"
  tags ={
    Name ="git17vpc"
  }
}