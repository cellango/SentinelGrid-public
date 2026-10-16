# Core add-ons. Customize versions/values as needed.

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.8.1"

  values = [
    yamlencode({
      clusterName = module.eks.cluster_name
      region      = var.aws_region
      vpcId       = module.vpc.vpc_id
    })
  ]
}

resource "helm_release" "external_dns" {
  name       = "external-dns"
  repository = "https://kubernetes-sigs.github.io/external-dns/"
  chart      = "external-dns"
  namespace  = "kube-system"
  version    = "1.14.5"

  values = [
    yamlencode({
      provider      = "aws"
      policy        = "sync"
      registry      = "txt"
      txtOwnerId    = module.eks.cluster_name
      domainFilters = var.external_dns_domain_filters
    })
  ]
}

resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  namespace  = "cert-manager"
  version    = "v1.15.1"

  create_namespace = true

  values = [
    yamlencode({
      installCRDs = true
    })
  ]
}

resource "helm_release" "keda" {
  name       = "keda"
  repository = "https://kedacore.github.io/charts"
  chart      = "keda"
  namespace  = "keda"
  version    = "2.14.0"
  create_namespace = true
}
